import os

class Config:
    SECRET_KEY=os.environ.get('SECRET_KEY')
    NEWS_API_KEY='9ec1c016660043a4892e9023a5e768b1'


class ProdConfig(Config):
    pass


class DevConfig(Config):
    DEBUG=True


config_options={
    'development': DevConfig,
    'production': ProdConfig
}