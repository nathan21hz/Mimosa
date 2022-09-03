import os
import pip

import config as cfg
cfg._init()
import utils.log as log
log._init()

cfg.load_config()

external_module_folder = cfg.get_value("EXTERNAL_MODULE_FOLDER","")

# Create external folder
if external_module_folder != "":
    print("Creating external folder...")
    if not os.path.exists(external_module_folder):
        os.mkdir(external_module_folder)
    if not os.path.exists(external_module_folder+"/source"):
        os.mkdir(external_module_folder+"/source")
    if not os.path.exists(external_module_folder+"/data"):
        os.mkdir(external_module_folder+"/data")
    if not os.path.exists(external_module_folder+"/renderer"):
        os.mkdir(external_module_folder+"/renderer")
    if not os.path.exists(external_module_folder+"/push"):
        os.mkdir(external_module_folder+"/push")

# Install external packages
if os.path.exists(external_module_folder+"/requirements.txt"):
    print("Installing external packages...")
    pip.main(["install","-r",external_module_folder+"/requirements.txt"])

# Create task config file
test_config_file = cfg.get_value("TASK_FILE", "tasks.json")
if not os.path.exists(test_config_file):
    with open(test_config_file,"w") as f:
        f.write("[]")