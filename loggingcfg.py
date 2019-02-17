import logging

loggers = {}


def initialize_logger(name='SZZ', console_level=logging.INFO):
    global loggers
    # avoids duplicate logging
    if loggers.get(name):
        logger = loggers.get(name)
    else:
        logger = logging.getLogger(name)
        if not len(logger.handlers):  # avoids duplicate logging
            logger.setLevel(console_level)
            # create console handler and set level to INFO
            ch = logging.StreamHandler()
            ch.setLevel(console_level)
            # create formatter
            formatter = logging.Formatter('[%(asctime)s - %(name)s - %(levelname)s]: %(message)s')
            # add formatter to ch
            ch.setFormatter(formatter)
            # add ch to logger
            logger.addHandler(ch)
            # file version of console output
            chf = logging.FileHandler('console.log')
            chf.setLevel(console_level)
            chf.setFormatter(formatter)
            logger.addHandler(chf)

            # create error file handler and set level to WARNING
            eh = logging.FileHandler('error.log')
            eh.setLevel(logging.WARNING)
            eh.setFormatter(formatter)
            logger.addHandler(eh)

            # create debug file handler and set level to DEBUG
            dh = logging.FileHandler('debug.log')
            dh.setLevel(logging.DEBUG)
            dh.setFormatter(formatter)
            logger.addHandler(dh)

    return logger


class ActorLogFilter(logging.Filter):
    def filter(self, log_record):
        return 'actorAddress' in log_record.__dict__


class NotActorLogFilter(logging.Filter):
    def filter(self, log_record):
        return 'actorAddress' not in log_record.__dict__


log_cfg = {'version': 1,
           'formatters': {'normal': {'format': '%(asctime)s - %(name)s - %(levelname)-8s %(message)s'},
                          'actor': {
                              'format': '%(asctime)s - %(name)s - %(levelname)-8s %(actorAddress)s => %(message)s'}
                          },
           'filters': {'isActorLog': {'()': ActorLogFilter},
                       'notActorLog': {'()': NotActorLogFilter}
                       },
           'handlers': {'h1': {'class': 'logging.FileHandler',
                               'filename': 'szz.log',
                               'formatter': 'normal',
                               'filters': ['notActorLog'],
                               'level': logging.INFO},
                        'h2': {'class': 'logging.FileHandler',
                               'filename': 'szz.log',
                               'formatter': 'actor',
                               'filters': ['isActorLog'],
                               'level': logging.WARNING},
                        },
           'loggers': {'SZZ': {'handlers': ['h1', 'h2'],
                               'level': logging.INFO
                               },
                       }
           }
