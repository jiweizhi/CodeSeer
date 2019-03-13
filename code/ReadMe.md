### Setup
1. **Java**
    * Requires maven version 3.3+
    * Requires jdk version 1.7+ (Preferably 1.8)
    * Set the environment variable **$JAVA_HOME** to the path where Java is installed
    * Preferably use an editor like [Intellij Idea](https://www.jetbrains.com/idea/)
    * Run `mvn clean install` to install all java dependencies
2. **Python**
    * Pip version 9.0+
    * Python version 2.7.6+
    * Run `pip install -r requirements.txt`
3. **Database**
    * The database we use is [Mongo DB](http://mongodb.github.io)
    * Install Mongo
    * Set the environment variable **$MONGO_HOME** to the path where Mongo is installed
    * Start: `sh scripts/common/start_mongo.sh &` or `mongostart`
    * Stop: `sh scripts/common/sh_stop_mongo.sh` or or `mongostop`
 
### Organization
* Jars
* meta_results
  * dataset 1(codejam)
    * clusters
    * functions
  * dataset 2(introclass)
* meta_store
  * dataset 1(codejam)
    * arguments
    * functions
  * dataset 2(introclass)
* resources
* scripts
  * common
  * dataset 1(codejam)
    * language 1(java)
    * language 2(python)
  * dataset 1(introclass)
* src
  * main
    * java
    * python
  * test
* target/
* pom.xml
* requirements.txt

### Example
Example programs are provided in   
   * [Java](https://github.com/dr-bigfatnoob/CodeSeer/tree/master/projects/src/main/java/Example)
   * [Python](https://github.com/dr-bigfatnoob/CodeSeer/tree/master/projects/src/main/python/Example)


### Tasks
1. **Download source - Only for CodeJam or IntroClassJava**
  * Run `sh scripts/<language>/download.sh 'dataset'`
  * Projects will be downloaded in `../projects/`
2. **Snip**
  * Run `sh scripts/<dataset>/<language>/snip_parallel.sh  'dataset'`
3. **Arguments - Metadata**
  * Java:
    * Store Objects: Run `sh scripts/java/store_objects.sh 'dataset'` 
    * Extract Primitive Arguments: Run `sh scripts/java/extract_primitive_arguments.sh  'dataset'`
    * Extract Fuzzed Arguments: Run `sh scripts/java/extract_fuzzed_arguments.sh  'dataset' <do_delete_old>`
    * Extract Metadata: Run `sh scripts/java/extract_metadata.sh  'dataset'`
  * Python:
    * Extract File Metadata: Run `sh scripts/java/extract_file_meta_data_parallel.sh  'dataset'`
    * Extract Metadata: Run `sh scripts/java/extract_metadata.sh  'dataset'`
  * Arguments were stored in `primitive_arguments` and `fuzzed_arguments` collection in MongoDB
4. **Execute**
  * Run `sh scripts/<language>/execute_parallel.sh 'dataset'`
  * Executed java functions stored in `functions_executed` and `py_functions_executed`
5. **Cluster**
  * Run `sh scripts/python/cluster.sh  'dataset'`
  * Results stored in `meta_results/<dataset>/clusters/`
