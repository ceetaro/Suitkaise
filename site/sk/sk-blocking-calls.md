/*

synced from suitkaise-docs/sk/blocking-calls.md

*/

rows = 2
columns = 1

# 1.1

title = "Blocking Calls Reference"

# 1.2

text = "
This page lists all function and method calls that the `sk` module auto-detects as blocking. If your code uses any of these, `.asynced()` and `.background()` become available.

Note: Detection is case-insensitive.

Note: You can always use the `@blocking` decorator to explicitly mark code as blocking when AST detection doesn't catch it (for things like heavy, time consuming CPU bound work)

---

## Exact Blocking Calls

These are matched exactly (full call path).

### Time / Sleep

- `time.sleep`
- `sleep`
- `timing.sleep`
- `suitkaise.timing.sleep`

### File I/O

- `open`
- `read`
- `write`
- `readline`
- `readlines`
- `writelines`

### OS Module

- `os.read`
- `os.write`
- `os.popen`
- `os.system`

### Subprocess

- `subprocess.run`
- `subprocess.call`
- `subprocess.check_call`
- `subprocess.check_output`
- `subprocess.popen`

### Requests

- `requests.get`
- `requests.post`
- `requests.put`
- `requests.delete`
- `requests.patch`
- `requests.head`
- `requests.options`
- `requests.request`

### HTTPX

- `httpx.get`
- `httpx.post`
- `httpx.put`
- `httpx.delete`
- `httpx.patch`
- `httpx.head`
- `httpx.options`
- `httpx.request`
- `httpx.stream`

### urllib / urllib3

- `urllib.request.urlopen`
- `urlopen`
- `urllib3.poolmanager.request`
- `urllib3.connectionpool.request`
- `urllib3.request`

### Socket

- `socket.socket`
- `socket.create_connection`

### Pathlib

- `pathlib.path.open`
- `pathlib.path.read_text`
- `pathlib.path.read_bytes`
- `pathlib.path.write_text`
- `pathlib.path.write_bytes`

### Shutil

- `shutil.copy`
- `shutil.copy2`
- `shutil.copyfile`
- `shutil.copytree`
- `shutil.move`
- `shutil.rmtree`

### Database Connectors

- `sqlite3.connect`
- `psycopg2.connect`
- `psycopg.connect`
- `pymysql.connect`
- `mysql.connector.connect`
- `mysqldb.connect`
- `pyodbc.connect`
- `duckdb.connect`
- `pymssql.connect`
- `oracledb.connect`
- `cx_oracle.connect`
- `snowflake.connector.connect`

### Redis

- `redis.from_url`
- `redis.redis.from_url`
- `redis.strictredis.from_url`
- `redis.sentinel.sentinel`

### MongoDB

- `pymongo.mongoclient`
- `pymongo.mongo_client.mongoclient`

### AWS / Boto3

- `boto3.client`
- `boto3.resource`
- `boto3.session.session.client`
- `boto3.session.session.resource`

### Kafka / RabbitMQ

- `kafka.kafka_producer`
- `kafka.kafkaconsumer`
- `confluent_kafka.producer`
- `confluent_kafka.consumer`
- `pika.blockingconnection`

### Elasticsearch / OpenSearch

- `elasticsearch.elasticsearch`
- `opensearchpy.opensearch`

### Database Cursor/Connection

- `cursor.execute`
- `cursor.executemany`
- `cursor.fetchone`
- `cursor.fetchall`
- `cursor.fetchmany`
- `connection.commit`
- `connection.rollback`

---

## Blocking Method Patterns

If any call ends with one of these method names, it's considered blocking.

### Core Blocking

- `sleep`
- `wait`
- `wait_for`
- `join`
- `acquire`

### Socket / Network

- `recv`
- `recvfrom`
- `send`
- `sendto`
- `sendall`
- `accept`
- `connect`
- `listen`

### File I/O

- `read`
- `readline`
- `readlines`
- `write`
- `writelines`
- `open`
- `read_text`
- `read_bytes`
- `write_text`
- `write_bytes`

### Database

- `fetch`
- `fetchone`
- `fetchall`
- `fetchmany`
- `execute`
- `executemany`
- `commit`
- `rollback`

### AWS S3

- `get_object`
- `put_object`
- `head_object`
- `list_objects`
- `list_objects_v2`
- `delete_object`
- `copy_object`
- `upload_file`
- `upload_fileobj`
- `download_file`
- `download_fileobj`
- `list_buckets`
- `create_bucket`
- `delete_bucket`

### AWS DynamoDB

- `get_item`
- `put_item`
- `update_item`
- `delete_item`
- `batch_get_item`
- `batch_write_item`
- `query`
- `scan`

### AWS SQS / SNS

- `send_message`
- `receive_message`
- `delete_message`
- `publish`
- `subscribe`

### MongoDB

- `find`
- `find_one`
- `insert_one`
- `insert_many`
- `update_one`
- `update_many`
- `replace_one`
- `delete_one`
- `delete_many`
- `aggregate`
- `count_documents`
- `distinct`
- `bulk_write`

### Redis

- `blpop`
- `brpop`
- `brpoplpush`
- `bzpopmin`
- `bzpopmax`
- `xread`
- `xreadgroup`
- `get_message`

### Elasticsearch / OpenSearch

- `search`
- `index`
- `bulk`
- `msearch`
- `delete_by_query`
- `update_by_query`

### Kafka / RabbitMQ

- `produce`
- `send`
- `poll`
- `flush`
- `basic_publish`
- `basic_consume`
- `basic_get`

### Other Databases

- `execute`
- `run`
- `query`
- `write_points`
- `write_api`

### Suitkaise

- `map`
- `imap`
- `starmap`
- `short`
- `trip`

---

## Broad Blocking Patterns

These method names are only considered blocking when the call path contains an I/O context keyword.

### Broad Methods

- `get`
- `set`
- `find`
- `insert`
- `update`
- `delete`
- `query`
- `scan`
- `request`
- `send`
- `recv`
- `read`
- `write`
- `execute`
- `commit`
- `rollback`

### I/O Context Keywords

For a broad method to trigger blocking detection, the call path must contain one of these:

#### Databases

- `db`
- `database`
- `cursor`
- `conn`
- `connection`
- `engine`
- `session`
- `pool`
- `psycopg`
- `postgres`
- `mysql`
- `sqlite`
- `mongo`
- `pymongo`
- `redis`
- `sqlalchemy`
- `odbc`
- `duckdb`

#### Cloud / AWS

- `boto3`
- `botocore`
- `s3`
- `sqs`
- `sns`
- `dynamodb`
- `kinesis`
- `lambda`

#### Messaging / Search

- `kafka`
- `rabbitmq`
- `amqp`
- `pika`
- `elasticsearch`
- `opensearch`
- `search`

#### Data Stores

- `cassandra`
- `neo4j`
- `influx`
- `influxdb`
- `clickhouse`

#### Networking

- `http`
- `https`
- `request`
- `requests`
- `httpx`
- `urllib`
- `socket`
- `sock`
- `client`
- `channel`

---

## Examples

### Detected as blocking

```python
time.sleep(1)                    # exact match: time.sleep
requests.get(url)                # exact match: requests.get
cursor.fetchall()                # pattern match: fetchall
self.db.execute(query)           # broad match: execute + db context
s3_client.get_object(...)        # pattern match: get_object
```

### NOT detected as blocking

```python
my_dict.get("key")               # broad method, no I/O context
data.update({"a": 1})            # broad method, no I/O context
calculate()                      # unknown function
```

### Use @blocking for undetected cases

```python
from suitkaise import sk, blocking

@sk
@blocking
def cpu_intensive():
    # pure computation, no I/O calls
    return sum(x**2 for x in range(10_000_000))
```
"
