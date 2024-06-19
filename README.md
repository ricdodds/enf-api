# ENF HTTP API

This repository hosts the code for the ENF API, a Flask-based web interface for the [ENF library](https://github.com/ricdodds/enf). 
It enables users to utilize the ENF library's functionality through HTTP endpoints.

The app can be deployed locally or on AWS. 

## Run Locally

You can run the app locally by following these steps:

```shell
docker-compose up
```

This will start the app at `http://localhost:5000`.

## Deploy on AWS

To deploy the app on AWS, you can use the provided Pulumi template.

First, install Pulumi:

```shell
curl -fsSL https://get.pulumi.com | sh
```

Then, deploy the app:

```shell
pulumi up
```

## API Endpoints

The app provides the following endpoints:

### POST `/match`

The `/match` endpoint allows clients to submit an audio file for matching against a specified dataset. 
The `year`, `month`, and `dataset` query parameters provide context for matching. 
The server responds with a task ID, which can be used to check the status of the processing task.

Query parameters

- **year**: The year for the data to be matched (integer).
- **month**: The month for the data to be matched (integer).
- **dataset**: The name of the dataset to be used for matching (string).

Body

- **file**: The audio file to be matched.

Example request:

```python
import requests

file_path = 'path/to/your/file.wav'

with open(file_path, 'rb') as file:
    response = requests.post(
        "http://localhost:5000/match", 
        files= {'file': file},
        params={
            'year': 2023,
            'month': 2,
            'dataset': 'eso'
        }
    )
    response.raise_for_status()

    print("Success:", response.json())
```

and a successful response

```json
{
    "task_id": "527d9822-310f-41f2-89c5-3fb5ed00845f"
}
```

### GET `/match/result/<task_id>`

The `/match/result/<task_id>` endpoint allows clients to check the status and result of a processing task.

Path parameters

- **task_id**: The ID of the processing task.

Example request:

```python
import requests

task_id = '527d9822-310f-41f2-89c5-3fb5ed00845f'

response = requests.get(
    f"http://localhost:5000/match/result/{task_id}"
)

print(response.json())
``` 

### GET `/datasets`

The `/datasets` endpoint allows clients to fetch the available datasets for matching.

Example request:

```python
import requests

response = requests.get(
    "http://localhost:5000/datasets"
)

print(response.json())
```

and a successful response

```json
{
    "datasets": ["eso"]
}
```

### GET `/datasets/<dataset>`

The `/datasets/<dataset>` endpoint allows clients to fetch the available months for a specific dataset.

Path parameters

- **dataset**: The name of the dataset.

Example request:

```python
import requests

response = requests.get(
    f"http://localhost:5000/datasets/eso"
)

print(response.json())
```

and a successful response

```json
{
    "months": [['2014', '1'], ['2014', '2'], ['2014', '3'], ...]
}
```
