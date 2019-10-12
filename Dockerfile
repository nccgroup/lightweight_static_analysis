FROM docker.pkg.github.com/github/semantic/semantic:sha_c1486db42dcbcc0a7748fc759017ab8d30d0f2d1 

RUN apt-get update -y \
	&& apt-get install -y locales

# Set the locale
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8 

RUN apt-get install -y jq python3 vim-nox python3-pip

RUN pip3 install ipdb
# RUN pip3 install -r requirements.txt

# RUN apt-get install -y ripgrep

