import sqlitecloud

# Direct connection string for testing
connection_string = 'sqlitecloud://crrdwstahk.g3.sqlite.cloud:8860/Metro?apikey=rG9S0rqIJtFAhLAdRfCbK0EcKP4nb8NW0NLJyPdS1Uc'

def get_connection():
    return sqlitecloud.connect(connection_string)
