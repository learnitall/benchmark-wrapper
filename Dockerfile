FROM registry.access.redhat.com/ubi8:latest

# Install and setup python 3.8
# Need to install 'wheel' and 'setuptools' in order to create wheel in the last step,
# and we will upgrade pip to make sure we are using the latest version
RUN dnf install --nodocs -y \
        python38 \
        python38-pip && \
    dnf clean all && \
    pip3 install --no-cache-dir --upgrade \
        pip \
        setuptools \
        wheel

# Install dnf dependencies needed for our packages
RUN dnf install --nodocs -y \
        gcc && \
    dnf clean all

# Install snafu dependencies from requirements file
COPY ./requirements/install/py38-requirements.txt /opt/snafu-requirements.txt
RUN pip3 install --no-cache-dir -r /opt/snafu-requirements.txt

# Install snafu using the wheel and then delete source
# Using a wheel and then deleting the source will save space in the image
COPY . /opt/snafu
RUN cd /opt/snafu && \
    python3 setup.py bdist_wheel --verbose && \
    pip3 install --no-cache-dir /opt/snafu/dist/snafu-*.whl && \
    rm -fr /opt/snafu
