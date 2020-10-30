# Notes

To activate virtulenv (Win): `../venv/Scripts/activate`


## How to run ECS test (in progress)

from within `/testing/citest` run:

```
$env:PYTHONPATH = ".;spinnaker_testing"; python tests/ecs_server_group_test.py --native_host=localhost --aws_profile=default-ca --test_aws_region=ca-central-1
```


### TODOs

[x] get test to run create/delete app
[x] get test to create/delete SG w/ inputs, w/o load balancing
[ ] get test to scale SG
[ ] get test to create/delete SG w/ inputs + load balancing
[ ] get test to create/delete SG w/ hardcoded artifact + load balancing



## Issues seen

* When running agaisnt `localhost`, test fails b/c HTML is returned by _scrape_spring_config()_ if `Deck` is being forwarded to `:9000`. 


## Useful debug cmds

* find test apps: `curl localhost:8084/applications | grep smoke`

* get task info: `curl localhost:8084/tasks/TASK_ID`


