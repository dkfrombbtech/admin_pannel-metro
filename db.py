import sqlitecloud

# Direct connection string for testing
connection_string = 'sqlitecloud://cczkici9nk.g5.sqlite.cloud:8860/Metro?apikey=lHMc0I4FP6R78gHytH7Mhll32cQxa4gxnEVMZGI3X3s'

def get_connection():
    return sqlitecloud.connect(connection_string)
