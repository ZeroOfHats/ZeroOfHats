# Use the official postgres:15-alpine image as the base
FROM postgres:15-alpine

# Allow for a custom initialization script
COPY ./initdb.d/*.sh /docker-entrypoint-initdb.d/
COPY ./initdb.d/*.sql /docker-entrypoint-initdb.d/
