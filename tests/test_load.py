from time import sleep

from locust import HttpUser, task, between, SequentialTaskSet, TaskSet


class HealthChecker(TaskSet):
    @task
    def heath_check(self):
        self.client.get('/')


class TestHealthCheck(HttpUser):
    tasks = [HealthChecker]
    wait_time = between(1, 2)


class DatasetUser(TaskSet):
    @task
    def datasets(self):
        self.client.get('/datasets')

    @task
    def eso_datasets(self):
        self.client.get('/datasets/eso')


class TestDatasets(HttpUser):
    tasks = [DatasetUser]
    wait_time = between(1, 2)


class MatchUser(SequentialTaskSet):
    def __init__(self, parent):
        super().__init__(parent)
        self.task_id = None

    @task
    def match(self):
        file_path = '../ENFormant/data/test_audio/output_ds.wav'

        res = self.client.post(
            '/match?db=eso&year=2023&month=2',
            files={'file': open(file_path, 'rb')}
        )

        self.task_id = res.json()['task_id']

    @task
    def result(self):
        res_url = f'/match/result/{self.task_id}'
        res = self.client.get(res_url, name='/match/result/[task_id]')

        while not res.json()["ready"]:
            sleep(3)
            res = self.client.get(res_url, name='/match/result/[task_id]')


class TestMatch(HttpUser):
    tasks = [MatchUser]
    wait_time = between(1, 2)
