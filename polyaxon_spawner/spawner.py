# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import os

from kubernetes import client, watch
from kubernetes.client.rest import ApiException

from polyaxon_schemas.polyaxonfile.polyaxonfile import PolyaxonFile
from polyaxon_schemas.utils import TaskType

from polyaxon_k8s import constants as k8s_constants
from polyaxon_k8s.exceptions import PolyaxonK8SError
from polyaxon_k8s.manager import K8SManager

from polyaxon_spawner.logger import logger
from polyaxon_spawner.templates import config_maps
from polyaxon_spawner.templates import constants
from polyaxon_spawner.templates import deployments
from polyaxon_spawner.templates import persistent_volumes
from polyaxon_spawner.templates import pods
from polyaxon_spawner.templates import services


class K8SSpawner(K8SManager):
    def __init__(self, polyaxonfile, k8s_config=None, namespace='default', in_cluster=False):
        super(K8SSpawner, self).__init__(k8s_config=k8s_config,
                                         namespace=namespace,
                                         in_cluster=in_cluster)
        self.polyaxonfile = PolyaxonFile.read(polyaxonfile)

        self.has_data_volume = False
        self.has_logs_volume = False
        self.has_files_volume = False

    @property
    def project_name(self):
        return self.polyaxonfile.project.name

    def _create_service(self, service, service_name):
        service_found = False
        try:
            self.k8s_api.read_namespaced_service(service_name, self.namespace)
            service_found = True
            logger.debug('A service with name `{}` was found'.format(service_name))
            self.k8s_api.patch_namespaced_service(service_name, self.namespace, service)
            logger.debug('Service `{}` was patched'.format(service_name))
        except ApiException as e:
            if service_found:
                raise PolyaxonK8SError(e)
            self.k8s_api.create_namespaced_service(self.namespace, service)
            logger.debug('Service `{}` was created'.format(service_name))

    def _get_pod_args(self, experiment, task_type, task_id, schedule):
        plxfiles_path = persistent_volumes.get_vol_path(project=self.project_name,
                                                        volume=constants.POLYAXON_FILES_VOLUME,
                                                        run_type=self.polyaxonfile.run_type)

        args = [
            "from polyaxon.polyaxonfile.local_runner import start_experiment_run; "
            "start_experiment_run('{polyaxonfile}', '{experiment_id}', "
            "'{task_type}', {task_id}, '{schedule}')".format(
                polyaxonfile=os.path.join(plxfiles_path, self.polyaxonfile.filename),
                experiment_id=experiment,
                task_type=task_type,
                task_id=task_id,
                schedule=schedule)]
        return args

    def _create_pod(self,
                    experiment,
                    task_type,
                    task_id,
                    command=None,
                    args=None,
                    restart_policy='Never'):
        task_name = constants.TASK_NAME.format(project=self.project_name,
                                               experiment=experiment,
                                               task_type=task_type,
                                               task_id=task_id)
        labels = pods.get_labels(project=self.project_name,
                                 experiment=experiment,
                                 task_type=task_type,
                                 task_id=task_id,
                                 task_name=task_name)
        ports = [constants.DEFAULT_PORT]

        volumes, volume_mounts = self.get_pod_volumes()
        pod = pods.get_pod(project=self.project_name,
                           experiment=experiment,
                           task_type=task_type,
                           task_id=task_id,
                           volume_mounts=volume_mounts,
                           volumes=volumes,
                           ports=ports,
                           command=command,
                           args=args,
                           restart_policy=restart_policy)

        pod_found = False
        try:
            self.k8s_api.read_namespaced_pod(task_name, self.namespace)
            pod_found = True
            logger.debug('A pod with name `{}` was found'.format(task_name))
            self.k8s_api.patch_namespaced_pod(task_name, self.namespace, pod)
            logger.debug('Pod `{}` was patched'.format(task_name))
        except ApiException as e:
            if pod_found:
                raise PolyaxonK8SError(e)
            self.k8s_api.create_namespaced_pod(self.namespace, pod)
            logger.debug('Pod `{}` was created'.format(task_name))

        service = services.get_service(name=task_name, labels=labels, ports=ports)
        self._create_service(service=service, service_name=task_name)

    def _delete_service(self, service_name):
        service_found = False
        try:
            self.k8s_api.read_namespaced_service(service_name, self.namespace)
            service_found = True
            self.k8s_api.delete_namespaced_service(service_name, self.namespace)
            logger.debug('Service `{}` deleted'.format(service_name))
        except ApiException as e:
            if service_found:
                logger.warning('Could not delete service `{}`'.format(service_name))
                raise PolyaxonK8SError(e)
            else:
                logger.debug('Service `{}` was not found'.format(service_name))

    def _delete_pod(self, experiment, task_type, task_id):
        task_name = constants.TASK_NAME.format(project=self.project_name,
                                               experiment=experiment,
                                               task_type=task_type,
                                               task_id=task_id)
        pod_found = False
        try:
            self.k8s_api.read_namespaced_pod(task_name, self.namespace)
            pod_found = True
            self.k8s_api.delete_namespaced_pod(
                task_name,
                self.namespace,
                client.V1DeleteOptions(api_version=k8s_constants.K8S_API_VERSION_V1))
            logger.debug('Pod `{}` deleted'.format(task_name))
        except ApiException as e:
            if pod_found:
                logger.warning('Could not delete pod `{}`'.format(task_name))
                raise PolyaxonK8SError(e)
            else:
                logger.debug('Pod `{}` was not found'.format(task_name))

        self._delete_service(task_name)

    def create_master(self, experiment=0):
        args = self._get_pod_args(experiment=experiment,
                                  task_type=TaskType.MASTER,
                                  task_id=0,
                                  schedule='train_and_evaluate')
        command = ["python3", "-c"]
        self._create_pod(experiment=experiment,
                         task_type=TaskType.MASTER,
                         task_id=0,
                         command=command,
                         args=args)

    def delete_master(self, experiment=0):
        self._delete_pod(experiment=experiment, task_type=TaskType.MASTER, task_id=0)

    def create_worker(self, experiment=0):
        n_pods = self.polyaxonfile.get_cluster_def_at(experiment)[0].get(TaskType.WORKER, 0)
        command = ["python3", "-c"]
        for i in range(n_pods):
            args = self._get_pod_args(experiment=experiment,
                                      task_type=TaskType.WORKER,
                                      task_id=i,
                                      schedule='train')
            self._create_pod(experiment=experiment,
                             task_type=TaskType.WORKER,
                             task_id=i,
                             command=command,
                             args=args)

    def delete_worker(self, experiment=0):
        n_pods = self.polyaxonfile.get_cluster_def_at(experiment)[0].get(TaskType.WORKER, 0)
        for i in range(n_pods):
            self._delete_pod(experiment=experiment, task_type=TaskType.WORKER, task_id=i)

    def create_ps(self, experiment=0):
        n_pods = self.polyaxonfile.get_cluster_def_at(experiment)[0].get(TaskType.PS, 0)
        command = ["python3", "-c"]
        for i in range(n_pods):
            args = self._get_pod_args(experiment=experiment,
                                      task_type=TaskType.PS,
                                      task_id=i,
                                      schedule='run_std_server')
            self._create_pod(experiment=experiment,
                             task_type=TaskType.PS,
                             task_id=i,
                             command=command,
                             args=args)

    def delete_ps(self, experiment=0):
        n_pods = self.polyaxonfile.get_cluster_def_at(experiment)[0].get(TaskType.PS, 0)
        for i in range(n_pods):
            self._delete_pod(experiment=experiment, task_type=TaskType.PS, task_id=i)

    def create_tensorboard_deployment(self):
        name = 'tensorboard'
        ports = [6006]
        volumes, volume_mounts = self.get_pod_volumes()
        logs_path = persistent_volumes.get_vol_path(project=self.project_name,
                                                    volume=constants.LOGS_VOLUME,
                                                    run_type=self.polyaxonfile.run_type)
        deployment = deployments.get_deployment(
            name=name,
            project=self.project_name,
            volume_mounts=volume_mounts,
            volumes=volumes,
            command=["/bin/sh", "-c"],
            args=["tensorboard --logdir={} --port=6006".format(logs_path)],
            ports=ports,
            role='dashboard')
        deployment_name = constants.DEPLOYMENT_NAME.format(project=self.project_name, name=name)

        deployment_found = False
        try:
            self.k8s_beta_api.read_namespaced_deployment(deployment_name, self.namespace)
            deployment_found = True
            logger.info('A deployment with name `{}` was found'.format(deployment_name))
            self.k8s_beta_api.patch_namespaced_deployment(
                deployment_name, self.namespace, deployment)
            logger.info('Deployment `{}` was patched'.format(deployment_name))
        except ApiException as e:
            if deployment_found:
                raise PolyaxonK8SError(e)
            self.k8s_beta_api.create_namespaced_deployment(self.namespace, deployment)
            logger.info('Deployment `{}` was created'.format(deployment_name))

        service = services.get_service(
            name=deployment_name,
            labels=deployments.get_labels(name=name, project=self.project_name, role='dashboard'),
            ports=ports,
            service_type='LoadBalancer')

        self._create_service(service=service, service_name=deployment_name)

    def delete_tensorboard_deployment(self):
        name = 'tensorboard'
        deployment_name = constants.DEPLOYMENT_NAME.format(project=self.project_name, name=name)
        pod_found = False
        try:
            self.k8s_beta_api.read_namespaced_deployment(deployment_name, self.namespace)
            pod_found = True
            self.k8s_beta_api.delete_namespaced_deployment(
                deployment_name,
                self.namespace,
                client.V1DeleteOptions(api_version=k8s_constants.K8S_API_VERSION_V1_BETA1,
                                       propagation_policy='Foreground'))
            logger.debug('Deployment `{}` deleted'.format(deployment_name))
        except ApiException as e:
            if pod_found:
                logger.warning('Could not delete deployment `{}`'.format(deployment_name))
                raise PolyaxonK8SError(e)
            else:
                logger.debug('Deployment `{}` was not found'.format(deployment_name))

        self._delete_service(deployment_name)

    def get_pod_volumes(self):
        volumes = []
        volume_mounts = []
        if self.has_data_volume:
            volumes.append(pods.get_volume(project=self.project_name,
                                           volume=constants.DATA_VOLUME))
            volume_mounts.append(pods.get_volume_mount(project=self.project_name,
                                                       volume=constants.DATA_VOLUME,
                                                       run_type=self.polyaxonfile.run_type))

        if self.has_logs_volume:
            volumes.append(pods.get_volume(project=self.project_name,
                                           volume=constants.LOGS_VOLUME))
            volume_mounts.append(pods.get_volume_mount(project=self.project_name,
                                                       volume=constants.LOGS_VOLUME,
                                                       run_type=self.polyaxonfile.run_type))

        if self.has_files_volume:
            volumes.append(pods.get_volume(project=self.project_name,
                                           volume=constants.POLYAXON_FILES_VOLUME))
            volume_mounts.append(pods.get_volume_mount(project=self.project_name,
                                                       volume=constants.POLYAXON_FILES_VOLUME,
                                                       run_type=self.polyaxonfile.run_type))

        return volumes, volume_mounts

    def _create_volume(self, volume):
        vol_name = constants.VOLUME_NAME.format(project=self.project_name, vol_name=volume)
        pvol = persistent_volumes.get_persistent_volume(project=self.project_name,
                                                        volume=volume,
                                                        run_type=self.polyaxonfile.run_type,
                                                        namespace=self.namespace)

        volume_found = False
        try:
            self.k8s_api.read_persistent_volume(vol_name)
            volume_found = True
            logger.debug('A volume with name `{}` was found'.format(vol_name))
            self.k8s_api.patch_persistent_volume(vol_name, pvol)
            logger.debug('Volume `{}` was patched'.format(vol_name))
        except ApiException as e:
            if volume_found:
                raise PolyaxonK8SError(e)
            self.k8s_api.create_persistent_volume(pvol)
            logger.debug('Volume `{}` was created'.format(vol_name))

        volc_name = constants.VOLUME_CLAIM_NAME.format(project=self.project_name, vol_name=volume)
        pvol_claim = persistent_volumes.get_persistent_volume_claim(project=self.project_name,
                                                                    volume=volume)
        volume_claim_found = False
        try:
            self.k8s_api.read_namespaced_persistent_volume_claim(volc_name, self.namespace)
            volume_claim_found = True
            logger.debug('A volume claim with name `{}` was found'.format(volc_name))
            self.k8s_api.patch_namespaced_persistent_volume_claim(volc_name,
                                                                  self.namespace,
                                                                  pvol_claim)
            logger.debug('Volume claim `{}` was patched'.format(volc_name))
        except ApiException as e:
            if volume_claim_found:
                raise PolyaxonK8SError(e)
            self.k8s_api.create_namespaced_persistent_volume_claim(self.namespace, pvol_claim)
            logger.debug('Volume claim `{}` was created'.format(volc_name))

    def create_data_volume(self):
        self._create_volume(constants.DATA_VOLUME)
        self.has_data_volume = True

    def create_logs_volume(self):
        self._create_volume(constants.LOGS_VOLUME)
        self.has_logs_volume = True

    def create_files_volumes(self):
        self._create_volume(constants.POLYAXON_FILES_VOLUME)
        self.has_files_volume = True

    def _delete_volume(self, volume):
        vol_name = constants.VOLUME_NAME.format(project=self.project_name, vol_name=volume)
        volume_found = False
        try:
            self.k8s_api.read_persistent_volume(vol_name)
            volume_found = True
            self.k8s_api.delete_persistent_volume(
                vol_name,
                client.V1DeleteOptions(api_version=k8s_constants.K8S_API_VERSION_V1))
            logger.debug('Volume `{}` Deleted'.format(vol_name))
        except ApiException as e:
            if volume_found:
                logger.warning('Could not delete volume `{}`'.format(vol_name))
                raise PolyaxonK8SError(e)
            else:
                logger.debug('Volume `{}` was not found'.format(vol_name))

        volc_name = constants.VOLUME_CLAIM_NAME.format(project=self.project_name, vol_name=volume)
        volume_claim_found = False
        try:
            self.k8s_api.read_namespaced_persistent_volume_claim(volc_name, self.namespace)
            volume_claim_found = True
            self.k8s_api.delete_namespaced_persistent_volume_claim(
                volc_name,
                self.namespace,
                client.V1DeleteOptions(api_version=k8s_constants.K8S_API_VERSION_V1))
            logger.debug('Volume claim `{}` Deleted'.format(volc_name))
        except ApiException as e:
            if volume_claim_found:
                logger.warning('Could not delete volume claim `{}`'.format(volc_name))
                raise PolyaxonK8SError(e)
            else:
                logger.debug('Volume claim `{}` was not found'.format(volc_name))

    def delete_data_volume(self):
        self._delete_volume(constants.DATA_VOLUME)
        self.has_data_volume = False

    def delete_logs_volume(self):
        self._delete_volume(constants.LOGS_VOLUME)
        self.has_logs_volume = False

    def delete_files_volumes(self):
        self._delete_volume(constants.POLYAXON_FILES_VOLUME)
        self.has_files_volume = False

    def delete_volumes(self):
        self.delete_data_volume()
        self.delete_logs_volume()
        self.delete_files_volumes()

    def create_volumes(self):
        self.create_data_volume()
        self.create_logs_volume()
        self.create_files_volumes()

    def create_cluster_config_map(self, experiment=0):
        name = constants.CONFIG_MAP_CLUSTER_NAME.format(project=self.project_name,
                                                        experiment=experiment)
        config_map = config_maps.get_cluster_config_map(
            project=self.project_name,
            experiment=experiment,
            cluster_def=self.polyaxonfile.get_cluster().to_dict())

        self.create_or_update_config_map(name=name, body=config_map, reraise=True)

    def delete_cluster_config_map(self, experiment=0):
        name = constants.CONFIG_MAP_CLUSTER_NAME.format(project=self.project_name,
                                                        experiment=experiment)
        self.delete_config_map(name, reraise=True)

    def create_experiment(self, experiment=0):
        self.create_cluster_config_map(experiment)
        self.create_volumes()
        self.create_master(experiment)
        self.create_worker(experiment)
        self.create_ps(experiment)

    def delete_experiment(self, experiment=0):
        self.delete_cluster_config_map(experiment)
        self.delete_volumes()
        self.delete_master(experiment)
        self.delete_worker(experiment)
        self.delete_ps(experiment)

    def create_all_experiments(self):
        for xp in range(self.polyaxonfile.matrix_space):
            self.create_experiment(xp)

    def delete_all_experiments(self):
        for xp in range(self.polyaxonfile.matrix_space):
            self.delete_experiment(xp)

    def get_experiment_status(self, experiment=0):
        return self.get_task_status(experiment=experiment,
                                    task_type=TaskType.MASTER,
                                    task_id=0)

    def get_task_status(self, experiment, task_type, task_id):
        task_name = constants.TASK_NAME.format(project=self.project_name,
                                               experiment=experiment,
                                               task_type=task_type,
                                               task_id=task_id)
        return self.k8s_api.read_namespaced_pod_status(task_name, self.namespace).status.phase

    def get_task_log(self, experiment, task_type, task_id, **kwargs):
        task_name = constants.TASK_NAME.format(project=self.project_name,
                                               experiment=experiment,
                                               task_type=task_type,
                                               task_id=task_id)
        return self.k8s_api.read_namespaced_pod_log(task_name, self.namespace, **kwargs)

    def watch_task_log(self, experiment, task_type, task_id, **kwargs):
        w = watch.Watch()
        for event in w.stream(self.get_task_log(experiment,
                                                task_type,
                                                task_id,
                                                follow=True,
                                                **kwargs)):
            print("Event: %s %s %s" % (
                event['type'], event['object'].kind, event['object'].metadata.name))
