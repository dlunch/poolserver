net = 'bitcoin_testnet'
target_difficulty = 1
generation_address = 'mg3jVmKBGjmoYrU4aGQYc3P6MZx8Nwmpqk'
longpoll_uri = '/lp'

extranonce2_size = 4

worker_host = '0.0.0.0'
worker_port = 9332

#Empty values will be filled from bitcoin.conf
rpc_host = ''
rpc_port = None
rpc_username = ''
rpc_password = ''

#You can use any dbapi-2.0 compliant database module here.
db_string = "dbname=pool user=pool"

import psycopg2
db_connection = psycopg2.connect(db_string)
