FROM postgres
COPY hstore.sql /docker-entrypoint-initdb.d
