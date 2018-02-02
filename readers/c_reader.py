from __future__ import print_function, division
import sys
import os
sys.path.append(os.path.abspath("."))
sys.dont_write_bytecode = True

__author__ = "bigfatnoob"


import csv
import random
import re
from utils import cache, lib
import logging
from utils.logger import get_logger
from sklearn.feature_extraction.text import CountVectorizer
from joblib import Parallel, delayed
from utils import google_storage

LOG_LEVEL = logging.INFO

logger = get_logger(__name__, LOG_LEVEL)

csv.field_size_limit(sys.maxsize)


def handled_csv_reader(csv_reader):
  """
  A modified version of CSV reader with handles CSV formatting error
  :param csv_reader: CSV reader
  :return:
  """
  while True:
    try:
      yield next(csv_reader)
    except csv.Error:
      pass
    continue
  return


def get_header_and_row_count(file_name):
  """
  Access header and get number of rows
  in the csv file
  :param file_name: Name of csv file
  :return: (Header, Number of rows in csv file)
  """
  with open(file_name, "rb") as csv_file:
    header = None
    header_reader = handled_csv_reader(csv.reader(csv_file))
    cnt = 0
    for row in header_reader:
      if header is None:
        header = row
      else:
        cnt += 1
    return header, cnt


def comment_remover(text):
  def replacer(match):
    s = match.group(0)
    if s.startswith('/'):
      return ""
    else:
      return s

  pattern = re.compile(
      r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
      re.DOTALL | re.MULTILINE
  )
  return re.sub(pattern, replacer, text)


def clean_and_dump(file_name, select_prob=1.0):
  prefix = file_name.rsplit("/", 1)[-1].split(".")[0]
  logger.info("Running for %s" % prefix)
  with open(file_name) as csv_file:
    header = None
    header_reader = csv.reader(csv_file)
    for row in header_reader:
      header = row
      break
    reader = csv.DictReader(csv_file, header)
    cnt = 0
    cleaned = []
    for row in reader:
      if random.random() > select_prob:
        continue
      cnt += 1
      # print(cnt)
      cleaned.append(comment_remover(row['content']))
  save_file = "data/cfiles_dump/cleaned/%s.pkl" % prefix
  cache.save(save_file, cleaned)


def dump_clean_folder(folder, select_prob=1.0):
  files = sorted(os.listdir(folder))
  for i, f_name in enumerate(files):
    if f_name == ".DS_Store":
      continue
    clean_and_dump("%s/%s" % (folder, f_name), select_prob)
    logger.info("Completed %d of %d" % (i + 1, len(files)))


def tokenize(file_name, token_pattern=r"(?u)\b[a-zA-Z_]{1,100}\b"):
  prefix = file_name.rsplit("/", 1)[-1].split(".")[0]
  logger.info("Running Tokenizer for %s" % prefix)
  analyzer = CountVectorizer(token_pattern=token_pattern).build_analyzer()
  snippets = cache.load(file_name)
  tokenized = []
  for snippet in snippets:
    tokenized.append(analyzer(snippet))
  save_file = "data/cfiles_dump/tokenized/%s.pkl" % prefix
  cache.save(save_file, tokenized)


def tokenize_folder(folder):
  files = sorted(os.listdir(folder))
  for i, f_name in enumerate(files):
    if f_name == ".DS_Store":
      continue
    tokenize("%s/%s" % (folder, f_name))
    logger.info("Completed %d of %d" % (i + 1, len(files)))


def c_compile(name, source):
  """
  Compile c source code.
  :param name: Name of file
  :param source: "Source code as string"
  :return:
  """
  try:
    with open("temp/%s.c" % name, "wb") as write:
      write.write(source)
    status = os.system("gcc -w temp/%s.c -o temp/%s > /dev/null 2>&1" % (name, name))
    cache.delete("temp/%s.c" % name)
    cache.delete("temp/%s" % name)
  except IOError:
    return 256
  return status


def save_valids(file_name, destination_path):
  """
  Save valid C files from csv
  :param file_name: Path of csv file
  :param destination_path: Path of destination
  """
  prefix = file_name.rsplit("/", 1)[-1].split(".")[0]
  logger.info("Running for %s" % prefix)
  temp_file = cache.create_file_path("%s/pkl/" % destination_path, prefix, ext=".tmp")
  stats_file = cache.create_file_path("%s/stats/" % destination_path, prefix, ext=".pkl")
  valid_file = cache.create_file_path("%s/pkl/" % destination_path, prefix, ext=".pkl")
  if cache.file_exists(valid_file):
    logger.info("%s file exists" % valid_file)
    return
  if cache.file_exists(temp_file):
    logger.info("%s file being processed" % valid_file)
    return
  cache.save(temp_file, {"Processing": True})
  header, row_count = get_header_and_row_count(file_name)
  with open(file_name) as csv_file:
    header_reader = handled_csv_reader(csv.reader(csv_file))
    for _ in header_reader: break
    reader = handled_csv_reader(csv.DictReader(csv_file, header))
    cnt = 0
    status_map = {}
    cache.mkdir("temp")
    valids = []
    for row in reader:
      try:
        cnt += 1
        name = row['path'].rsplit("/", 1)[-1].split(".")[0].split()[0]
        status = c_compile(name, comment_remover(row['content']))
        if status == 0:
          valids.append(row)
        status_map[status] = status_map.get(status, 0) + 1
        if cnt % 100 == 0:
          logger.info("Index: %s; Processed: %d / %d; Status so far: %s" % (prefix, cnt, row_count, status_map))
      except IndexError:
        pass
    cache.save(stats_file, status_map)
    cache.save(valid_file, valids)
    cache.delete(temp_file)
    logger.info("SAVING: %s; Processed: %d; Status: %s" % (prefix, cnt, status_map))


def save_valids_in_folder(folder, destination_path, n_jobs=1):
  """
  Save commented functions from pkl files in a folder in parallel manner
  :param folder: Path of source folder
  :param destination_path: Path of destination
  :param n_jobs: Number of jobs to run in parallel
  """
  Parallel(n_jobs=n_jobs)(delayed(save_valids)(file_name, destination_path)
                          for file_name in sorted(cache.list_files(folder, is_relative=False)))


def aggregate_valid_files(folder):
  """
  Aggregate all valid files in the folder
  :param folder:
  :return:
  """
  valid_rows = []
  logger.info("Aggregating valid records into one file.")
  for f in cache.list_files(cache.create_file_path(folder, "pkl", ext=None), is_relative=False):
    rows = cache.load(f)
    if rows is None: continue
    for row in rows:
      valid_rows.append(row)
  valid_file = cache.create_file_path(folder, "valid", ext=".pkl")
  cache.save(valid_file, valid_rows)
  logger.info("Saved in %s" % valid_file)


def aggregate_valid_status(folder):
  """
  Aggregate valids status in folder
  :param folder:
  :return:
  """
  valid_status = {}
  logger.info("Aggregating valid status.")
  for f in cache.list_files(cache.create_file_path(folder, "stats", ext=None), is_relative=False):
    status = cache.load(f)
    if status is None: continue
    for key, val in status.items():
      valid_status[key] = valid_status.get(key, 0) + val
  total = sum(valid_status.values())
  valids = valid_status[0]
  report = {
      "total": total,
      "valids": valids,
      "percentage": valids * 100 / total,
      "_raw": valid_status
  }
  valid_status_file = cache.create_file_path(folder, "status", ext=".pkl")
  cache.save(valid_status_file, report)
  logger.info("Saved in %s" % valid_status_file)
  logger.info("Ran: %d; Valid: %d; %%age: %f" % (total, valids, report["percentage"]))


def download_clean_save(blob, download_path, valids_path):
  prefix = blob.rsplit("/", 1)[-1].split(".")[0]
  logger.info("Running for %s" % prefix)
  temp_file = cache.create_file_path("%s/pkl/" % valids_path, prefix, ext=".tmp")
  stats_file = cache.create_file_path("%s/stats/" % valids_path, prefix, ext=".pkl")
  valid_file = cache.create_file_path("%s/pkl/" % valids_path, prefix, ext=".pkl")
  if cache.file_exists(valid_file):
    logger.info("%s file exists" % valid_file)
    return
  if cache.file_exists(temp_file):
    logger.info("%s file being processed" % valid_file)
    return
  cache.save(temp_file, {"Processing": True})
  logger.info("Index: %s; Downloading: %s" % (prefix, blob))
  download_file = google_storage.download_blob(blob, download_path)
  header, row_count = get_header_and_row_count(download_file)
  with open(download_file) as csv_file:
    header_reader = handled_csv_reader(csv.reader(csv_file))
    for _ in header_reader: break
    reader = handled_csv_reader(csv.DictReader(csv_file, header))
    cnt = 0
    status_map = {}
    cache.mkdir("temp")
    valids = []
    for row in reader:
      try:
        cnt += 1
        name = row['path'].rsplit("/", 1)[-1].split(".")[0].split()[0]
        status = c_compile(name, comment_remover(row['content']))
        if status == 0:
          valids.append(row)
        status_map[status] = status_map.get(status, 0) + 1
        if cnt % 100 == 0:
          logger.info("Index: %s; Processed: %d / %d; Status so far: %s" % (prefix, cnt, row_count, status_map))
      except IndexError:
        pass
    cache.save(stats_file, status_map)
    cache.save(valid_file, valids)
    cache.delete(temp_file)
    cache.delete(download_file)
    logger.info("SAVING: %s; Processed: %d; Status: %s" % (prefix, cnt, status_map))


def download_clean_save_folder(prefix_path, base_path, download_ext, valids_ext, n_jobs=1, max_results=None):
  blobs = google_storage.list_blobs(prefix_path, max_results)
  download_path = cache.create_file_path(base_path, download_ext)
  valids_path = cache.create_file_path(base_path, valids_ext)
  Parallel(n_jobs=n_jobs)(delayed(download_clean_save)(blob, download_path, valids_path) for blob in blobs)


def _save_valids_in_folder():
  """
  Runner for saving valids in folder
  :return:
  """
  folder = "data/cfiles_dump/csv/"
  n_jobs = 1
  args = sys.argv
  if len(args) >= 2 and lib.is_int(args[1]):
    n_jobs = int(args[1])
  logger.info("Running as %d jobs" % n_jobs)
  save_valids_in_folder(folder, n_jobs)


def _aggregate():
  """
  Runner for aggregating
  :return:
  """
  folder = "data/cfiles_dump/valids"
  aggregate_valid_files(folder)
  aggregate_valid_status(folder)


def _download_clean_save_folder():
  prefix_path = "cfiles/csv_all"
  base_path = "data/cfiles_dump"
  download_ext = "csv_all"
  valids_ext = "valids_all"
  max_results = 1
  n_jobs = 1
  args = sys.argv
  if len(args) >= 2 and lib.is_int(args[1]):
    n_jobs = int(args[1])
  download_clean_save_folder(prefix_path, base_path, download_ext, valids_ext, n_jobs, max_results)


if __name__ == "__main__":
  # dump_clean_folder("data/cfiles_dump/csv", 0.2)
  # tokenize_folder("data/cfiles_dump/cleaned")
  # save_valids("data/cfiles_dump/csv/000000000000.csv", "data/cfiles_dump/valids")
  # _save_valids_in_folder()
  # _aggregate()
  _download_clean_save_folder()
