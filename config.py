import os

class Config:
    SECRET_KEY=os.environ.get('SECRET_KEY')
    NEWS_API_KEY='79636e40839742c78b5049f56ce3dcb2'


class ProdConfig(Config):
    pass


class DevConfig(Config):
    DEBUG=True


config_options={
    'development': DevConfig,
    'production': ProdConfig
}