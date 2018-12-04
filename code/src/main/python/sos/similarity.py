import sys
import os

sys.path.append(os.path.abspath("."))
sys.dont_write_bytecode = True

__author__ = "bigfatnoob"

from collections import defaultdict
from sklearn.cluster import DBSCAN
import numpy as np
import re

from utils import cache, logger, lib
from utils.lib import O
from utils.stat import Stat
from sos.function import Function, Outputs
from store import json_store, mongo_store
import properties


LOGGER = logger.get_logger(os.path.basename(__file__.split(".")[0]))


def get_store(dataset, is_test=False):
  if properties.STORE == "json":
    return json_store.FunctionStore(dataset)
  elif properties.STORE == "mongo":
    return mongo_store.FunctionStore(dataset, is_test=is_test)
  raise RuntimeError("Invalid configuration: %s" % properties.STORE)


def get_execution_store(dataset):
  if properties.STORE == "mongo":
    return mongo_store.ExecutionStore(dataset)
  raise RuntimeError("Invalid configuration: %s" % properties.STORE)


def execution_similarity(func1, func2):
  if func1.input_key != func2.input_key:
    return 0.0
  sames = 0.0
  alls = 0.0
  assert len(func1.outputs.returns) == len(func2.outputs.returns)
  for i in range(len(func1.outputs.returns)):
    alls += 1
    o1 = func1.outputs.returns[i]
    o2 = func2.outputs.returns[i]
    e1 = func1.outputs.errors[i]
    e2 = func2.outputs.errors[i]
    if o1 == o2 and e1 == e2:
      sames += 1
  return sames / alls


def execution_distance(func1, func2):
  return 1.0 - execution_similarity(func1, func2)


class Clusterer(O):
  def __init__(self, functions, **kwargs):
    self.functions = functions
    # noinspection PyUnresolvedReferences
    self.X = np.arange(len(self.functions)).reshape(-1, 1)
    O.__init__(self, **kwargs)

  def distance(self, x, y):
    return execution_distance(self.functions[int(x)], self.functions[int(y)])

  def cluster(self, file_name=None, skip_singles=False):
    dbs = DBSCAN(eps=0.01, min_samples=2, metric=self.distance)
    labels = dbs.fit_predict(self.X)
    clusters = defaultdict(list)
    for label, func in zip(labels, self.functions):
      if skip_singles and label == -1:
        continue
      clusters[label].append(func)
    file_contents = []
    for label, func_cluster in clusters.items():
      if label == -1: continue
      cluster_str = "\n\n****** Cluster %d ******" % label
      if file_name is not None: file_contents.append(cluster_str)
      for func in func_cluster:
        if file_name is not None: file_contents.append(func.body)
      cache.write_file(file_name, "\n".join(file_contents))
    return clusters


def load_functions(dataset, is_test=False, update_clone_meta=False):
  LOGGER.info("Loading java functions for '%s' ... " % dataset)
  data_store = get_store(dataset, is_test=is_test)
  functions_arr = data_store.load_functions()
  function_pattern = re.compile(r'^func_')
  functions = []
  for func_dict in functions_arr:
    if not function_pattern.match(func_dict['name']): continue
    function_metadata = data_store.load_metadata(func_dict)
    return_meta_data = function_metadata["return"]
    outputs = Outputs(func_dict["outputs"])
    funct = Function(name=func_dict["name"], dataset=dataset,
                     class_name=func_dict["class"], package=func_dict["package"],
                     input_key=func_dict["inputKey"], outputs=outputs,
                     lines_touched=function_metadata.get("linesTouched", None),
                     span=function_metadata.get("span", None), body=function_metadata["body"], source="java")
    if data_store.is_object_return(return_meta_data):
      cloned_function_names = get_execution_store(dataset).load_cloned_function_names(funct.name)
      updated_cloned_function_names = {}
      for attribute, returns in data_store.get_return_vals(outputs.returns).items():
        clone = funct.clone()
        clone.outputs = outputs.clone()
        clone.outputs.returns = returns[:]
        clone.return_attribute = attribute
        if cloned_function_names and attribute in cloned_function_names:
          clone.name = cloned_function_names[attribute]
        updated_cloned_function_names[attribute] = clone.name
        functions.append(clone)
      if update_clone_meta:
        get_execution_store(dataset).save_cloned_function_names(funct.name, updated_cloned_function_names)
    else:
      functions.append(funct)
  if is_test:
    return functions
  valid_functions = [func for func in functions if func.is_useful()]
  LOGGER.info("Valid Functions : %d / %d" % (len(valid_functions), len(functions)))
  return valid_functions


def load_py_functions(dataset, is_test=False):
  LOGGER.info("Loading python functions for '%s' ... " % dataset)
  data_store = get_store(dataset, is_test=is_test)
  functions_arr = data_store.load_py_functions()
  function_pattern = re.compile(r'^func_')
  functions = []
  for func_dict in functions_arr:
    if not function_pattern.match(func_dict['name']): continue
    function_metadata = data_store.load_py_metadata(func_dict['name'])
    outputs = Outputs(func_dict["outputs"])
    funct = Function(name=func_dict["name"], dataset=dataset,
                     input_key=func_dict["inputKey"], outputs=outputs,
                     lines_touched=function_metadata.get("linesTouched", None),
                     span=function_metadata.get("span", None), body=function_metadata["body"], source="python")
    functions.append(funct)
  if is_test:
    return functions
  valid_functions = [func for func in functions if func.is_useful()]
  LOGGER.info("Valid Functions : %d / %d" % (len(valid_functions), len(functions)))
  return valid_functions


def compute_similarity(dataset, language=None, functions=None, base_folder=None, file_name=None,
                       skip_singles=False, update_clone_meta=False):
  if not functions:
    if language == "java":
      functions = load_functions(dataset, update_clone_meta=update_clone_meta)
    elif language == "python":
      functions = load_py_functions(dataset)
    elif language == "java_python":
      functions = load_functions(dataset, update_clone_meta=update_clone_meta) + load_py_functions(dataset)
    else:
      raise RuntimeError("Invalid language: %s" % language)
    if dataset not in ["codejam", "introclass"]:
      raise RuntimeError("Invalid dataset: %s" % dataset)
  LOGGER.info("Clustering ... ")
  if file_name is None:
    file_name = language or "clusters"
    LOGGER.info("A @file_name is not provided. Reverting file name to '%s'" % file_name)
  if base_folder is None:
    base_folder = lib.get_clusters_folder(dataset)
  clusters_txt_file = os.path.join(base_folder, "%s.txt" % file_name)
  clusters_pkl_file = os.path.join(base_folder, "%s.pkl" % file_name)
  clusters_report_file = os.path.join(base_folder, "%s.md" % file_name)
  clusters = Clusterer(functions).cluster(clusters_txt_file, skip_singles=skip_singles)
  cache.save_pickle(clusters_pkl_file, clusters)
  n_clusters = len(clusters)
  sizes = [len(cluster_funcs) for label, cluster_funcs in clusters.items() if label != -1]
  meta_data = "## Cluster sizes\n"
  meta_data += "* Number of clusters: %d\n" % n_clusters
  meta_data += "* Number of functions clustered: %d\n" % sum(sizes)
  meta_data += "* Number of functions not clustered: %d\n\n" % (len(functions) - sum(sizes))
  meta_data += "## REPORT\n"
  meta_data += Stat(sizes).report()
  cache.write_file(clusters_report_file, meta_data)


"""
Validity
"""


def _test_function():
  dataset = "codejam"
  data_store = get_store("codejam")
  func_dict = data_store.load_function("func_b1d6e0e04b4f4065870c60fcba28ff0c")
  function_metadata = data_store.load_metadata(func_dict)
  outputs = Outputs(func_dict["outputs"])
  funct = Function(name=func_dict["name"], dataset=dataset,
                   class_name=func_dict["class"], package=func_dict["package"],
                   input_key=func_dict["inputKey"], outputs=outputs,
                   lines_touched=function_metadata.get("linesTouched", None),
                   span=function_metadata.get("span", None), body=function_metadata["body"], source="java")
  print func_dict
  print(funct.is_useful())


def _test_functions():
  load_functions("codejam")
  load_py_functions("codejam")


def _main():
  args = sys.argv
  if len(args) < 2:
    print("""
    python sos/similiarity <dataset> <?language>
    dataset: codejam/introclass
    language: java(default)/python/java_python
    """)
    exit(0)
  language = args[2] if len(args) >= 3 else "java"
  compute_similarity(args[1], language, skip_singles=True, update_clone_meta=True)


if __name__ == "__main__":
  _main()
