import sys
import os

sys.path.append(os.path.abspath("."))
sys.dont_write_bytecode = True

__author__ = "bigfatnoob"


from store import base_store, mongo_driver
from utils import logger
import properties
import re

LOGGER = logger.get_logger(os.path.basename(__file__.split(".")[0]))


class InputStore(base_store.InputStore):
  def __init__(self, dataset, **kwargs):
    base_store.InputStore.__init__(self, dataset, **kwargs)

  def load_inputs(self, args_key):
    arguments = mongo_driver.get_collection(self.dataset, "fuzzed_args").find_one({"key": args_key})["args"]
    assert len(arguments) == properties.FUZZ_ARGUMENT_SIZE
    if self.is_array(arguments):
      key_args = arguments
    else:
      key_args = [[] for _ in range(len(arguments[0]))]
      for i in range(len(arguments[0])):
        for arg in arguments:
          key_args[i].append(arg)
    return key_args


class FunctionStore(base_store.FunctionStore):
  def __init__(self, dataset, **kwargs):
    base_store.FunctionStore.__init__(self, dataset, **kwargs)

  def load_function(self, function_name):
    collection = mongo_driver.get_collection(self.dataset, "functions_executed")
    return collection.find_one({"name": function_name})

  def load_functions(self):
    collection = mongo_driver.get_collection(self.dataset, "functions_executed")
    return collection.find()

  def load_metadata(self, funct):
    return mongo_driver.get_collection(self.dataset, "functions_metadata").find_one({"name": funct["name"]})

  def update_function_arg_type(self, function_name, function_arg_types):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_arg_types")
    if not mongo_driver.is_collection_exists(collection):
      mongo_driver.create_index_for_collection(collection, "name")
    collection.insert({
      "name": function_name,
      "types": function_arg_types
    })

  def load_function_arg_type(self, function_name):
    try:
      return mongo_driver.get_collection(self.dataset, "py_functions_arg_types").find_one({"name": function_name})
    except Exception as e:
      LOGGER.critical("Failed to load args for function: '%s'. Returning None.\nMessage: %s" % (function_name, e.message))
      return None

  def save_py_function(self, function_json):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_executed")
    if not mongo_driver.is_collection_exists(collection):
      mongo_driver.create_index_for_collection(collection, "name")
    try:
      collection.insert(function_json)
    except Exception:
      del function_json['outputs']
      self.save_failed_py_function(function_json)

  def load_py_function(self, function_name):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_executed")
    return collection.find_one({"name": function_name})

  def exists_py_function(self, function_name):
    return self.load_py_function(function_name) is not None

  def save_failed_py_function(self, function_json):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_failed")
    if not mongo_driver.is_collection_exists(collection):
      mongo_driver.create_index_for_collection(collection, "name")
    collection.insert(function_json)

  def is_invalid_py_function(self, function_name):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_failed")
    return collection.find_one({"name": function_name}) is not None

  def load_py_functions(self):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_executed")
    return collection.find()

  def save_py_metadata(self, func_json):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_metadata")
    if not mongo_driver.is_collection_exists(collection):
      mongo_driver.create_index_for_collection(collection, "name")
    collection.insert(func_json)

  def load_py_metadata(self, function_name):
    collection = mongo_driver.get_collection(self.dataset, "py_functions_metadata")
    return collection.find_one({"name": function_name})


class PyFileMetaStore(base_store.PyFileMetaStore):
  def __init__(self, dataset, **kwargs):
    base_store.PyFileMetaStore.__init__(self, dataset,  **kwargs)

  def load_meta(self, file_name):
    sep_positions = [m.start() for m in re.finditer(os.sep, file_name)]
    if sep_positions and len(sep_positions) > 3:
      fp_regex = file_name[sep_positions[2]:]
    else:
      fp_regex = file_name
    collection = mongo_driver.get_collection(self.dataset, "py_file_meta")
    return collection.find_one({"file_path": {"$regex": fp_regex}})

  def save_meta(self, bson_dict):
    collection = mongo_driver.get_collection(self.dataset, "py_file_meta")
    if not mongo_driver.is_collection_exists(collection):
      mongo_driver.create_index_for_collection(collection, "file_path")
    collection.insert(bson_dict)


class ArgumentStore(base_store.ArgumentStore):
  def __init__(self, dataset, **kwargs):
    base_store.ArgumentStore.__init__(self, dataset, **kwargs)

  def load_args(self, args_key):
    collection = mongo_driver.get_collection(self.dataset, "fuzzed_args")
    try:
      return collection.find_one({"key": args_key})
    except Exception as e:
      LOGGER.exception("Failed to load args with key: '%s'. Returning None" % args_key, e)
      return None
