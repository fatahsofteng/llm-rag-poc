FROM postgres:15

# Install pgvector and pg_bigm dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    git \
    postgresql-server-dev-15 \
    libicu-dev \
    && rm -rf /var/lib/apt/lists/*

# Install pgvector
RUN cd /tmp && \
    git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git && \
    cd pgvector && \
    make && \
    make install && \
    cd / && \
    rm -rf /tmp/pgvector

# Install pg_bigm
RUN cd /tmp && \
    git clone https://github.com/pgbigm/pg_bigm.git && \
    cd pg_bigm && \
    make USE_PGXS=1 && \
    make USE_PGXS=1 install && \
    cd / && \
    rm -rf /tmp/pg_bigm

# Configure PostgreSQL for pg_bigm
RUN echo "shared_preload_libraries = 'pg_bigm'" >> /usr/share/postgresql/postgresql.conf.sample

# Clean up
RUN apt-get purge -y --auto-remove build-essential postgresql-server-dev-15 git