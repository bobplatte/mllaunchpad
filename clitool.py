import getopt
import sys
from flask import Flask
import launchpad as lp
from launchpad import logutil

HELP_STRING = '''
Parameters:
-h        / --help               : Print this help
-t        / --train              : Run training, store model and metrics
-r        / --retest             : Retest model, update metrics
-a        / --api                : Run API Server (Debug Mode!)
-c <file> / --config=<file>      : Config file to use
-l <file> / --logconfig=<file>   : Log config file to use
'''


if __name__ == '__main__':
    fullCmdArguments = sys.argv
    argumentList = fullCmdArguments[1:]
    unixOptions = 'htrac:l:'
    gnuOptions = ['help', 'train', 'retest', 'api', 'config=', 'logconfig=']
    try:
        arguments, values = getopt.getopt(argumentList, unixOptions, gnuOptions)
    except getopt.error as err:
        # output error, and return with an error code
        print(str(err))
        sys.exit(2)
    # evaluate given options
    cmd = None
    conf = None
    logger = None
    for currentArgument, currentValue in arguments:
        if currentArgument in ('-c', '--config'):
            conf = lp.get_validated_config(currentValue)
        elif currentArgument in ('-l', '--logconfig'):
            logger = logutil.init_logging(currentValue)
        elif currentArgument in ('-t', '--train'):
            cmd = 'train'
        elif currentArgument in ('-r', '--retest'):
            cmd = 'retest'
        elif currentArgument in ('-a', '--api'):
            cmd = 'api'
        elif currentArgument in ('-h', '--help'):
            print(HELP_STRING)
            exit(0)

    if cmd is None:
        print('\nNo command given.')
        print(HELP_STRING)
        exit(1)

    logger = logger or logutil.init_logging()
    conf = conf or lp.get_validated_config()
    if cmd == 'train':
        model, metrics = lp.train_model(conf)
    elif cmd == 'retest':
        metrics = lp.retest_model(conf)
    elif cmd == 'api':
        logger.warning("Starting Flask debug server. In production, please use a WSGI server, "
                       + "e.g. 'gunicorn -w 4 -b 127.0.0.1:5000 launchpad.entrypoint:app'")
        app = Flask(__name__)
        lp.ModelApi(conf, app)
        app.run(debug=True)
