import os

class Config:
    SECRET_KEY=os.environ.get('SECRET_KEY')
    NEWS_API_KEY='REMOVED'


class ProdConfig(Config):
    pass


class DevConfig(Config):
    DEBUG=True


config_options={
    'development': DevConfig,
    'production': ProdConfig
}