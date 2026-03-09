FROM ubuntu:24.04

RUN yes | unminimize

RUN DEBIAN_FRONTEND=noninteractive apt-get update && apt-get install -y git curl ca-certificates wget htop vim jq sudo gnupg zsh tmux xz-utils make adduser unzip zstd
j
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN curl -fsSL https://ollama.com/install.sh | sh

ARG USERNAME=ubuntu
RUN echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} && \
    chmod 0440 /etc/sudoers.d/${USERNAME}

USER ${USERNAME}

ARG CONTAINER_WORKSPACE_FOLDER
ENV VIRTUAL_ENV="${CONTAINER_WORKSPACE_FOLDER}/.venv"
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"