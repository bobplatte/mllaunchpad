from . import resource
from .model_interface import ModelInterface, ModelMakerInterface
import logging

logger = logging.getLogger(__name__)


def _model_key(model_conf):
    return model_conf['name'] + "_" + model_conf['version']


_cached_model_stores = {}
_cached_model_tuples = {}
_cached_data_source_sink_tuples = {}
_cached_model_makers = {}


def _get_model_maker_cached(complete_conf):
    """Locate and instantiate class of data-scientist-provided ModelMaker
    (which the data scientist inherited from ModelMakerInterface).
    For this to work, your model module (.py file) needs to be in python's
    sys.path (usually the case).
    Also set the config's model: module property accordingly.

    Params:
        complete_conf: the configuration dict

    Returns:
        instance of data scientist's ModelMaker model factory object
    """
    global _cached_model_makers

    key = _model_key(complete_conf['model'])

    mm = _cached_model_makers.get(key)
    if mm is None:
        logger.debug('Locating and instantiating ModelMaker...')

        __import__(complete_conf['model']['module'])

        classes = ModelMakerInterface.__subclasses__()
        if len(classes) != 1:
            raise ValueError('The configured model module (.py file) must contain '
                             + 'one ModelMakerInterface-inheriting class definition, but contains {}.'
                             .format(len(classes)))

        mm_cls = classes[0]
        logger.debug('Found ModelMaker class named %s', mm_cls)

        mm = mm_cls()
        _cached_model_makers[key] = mm

        logger.debug('Instantiated ModelMaker object %s', mm)

    return mm


def _get_model_store_cached(complete_conf):
    global _cached_model_stores

    key = _model_key(complete_conf['model'])

    model_store = _cached_model_stores.get(key) or resource.ModelStore(complete_conf)
    _cached_model_stores[key] = model_store

    return model_store


def _get_model_cached(complete_conf):
    global _cached_model_tuples
    model_store = _get_model_store_cached(complete_conf)

    model_conf = complete_conf['model']
    key = _model_key(model_conf)

    model_tuple = _cached_model_tuples.get(key)
    if model_tuple is None:
        logger.info('Loading model...')
        model, meta = model_store.load_trained_model(model_conf)
        logger.info('Model loaded: {}, version: {}, created {}'
                    .format(meta['name'], meta['version'], meta['created']))

        model_tuple = (model, meta)
        _cached_model_tuples[key] = model_tuple

    return model_tuple


def _get_data_sources_and_sinks_cached(complete_conf, tags=None):
    global _cached_data_source_sink_tuples

    key = _model_key(complete_conf['model'])

    ds_tuple = _cached_data_source_sink_tuples.get(key)
    if ds_tuple is None:
        logger.info('Initializing datasources...')
        dso, dsi = resource.create_data_sources_and_sinks(complete_conf, tags=tags)
        logger.info('%s datasource(s) initialized: %s', len(dso), list(dso.keys()))
        logger.info('%s datasink(s) initialized: %s', len(dsi), list(dsi.keys()))

        ds_tuple = (dso, dsi)
        _cached_data_source_sink_tuples[key] = ds_tuple

    return ds_tuple


def train_model(complete_conf):
    logger.debug('Creating trained model...')
    user_mm = _get_model_maker_cached(complete_conf)

    dso, dsi = _get_data_sources_and_sinks_cached(complete_conf, tags=['train', 'test'])

    model_conf = complete_conf['model']

    try:
        logger.debug('Trying to load old model...')
        old_model, meta = _get_model_cached(complete_conf)
        logger.info('Loaded old model %s %s', meta['name'], meta['version'])
    except FileNotFoundError:
        logger.info('No old model to load')
        old_model = None

    model: ModelInterface = user_mm.create_trained_model(model_conf, dso, dsi, old_model=old_model)

    if not isinstance(model, ModelInterface):
        logger.warning('Model\'s class is not a subclass of ModelInterface: %s', model)

    logger.debug('Testing trained model...')
    metrics = user_mm.test_trained_model(model_conf, dso, dsi, model)

    model_store = _get_model_store_cached(complete_conf)
    model_store.dump_trained_model(complete_conf, model, metrics)

    logger.info('Created and stored trained model %s, version %s, metrics %s',
                model_conf['name'], model_conf['version'], metrics)

    return model, metrics


def retest(complete_conf):
    logger.debug('Retesting existing trained model...')
    user_mm = _get_model_maker_cached(complete_conf)

    dso, dsi = _get_data_sources_and_sinks_cached(complete_conf, tags='test')

    model, metadata = _get_model_cached(complete_conf)

    model_conf = complete_conf['model']
    test_metrics = user_mm.test_trained_model(model_conf, dso, dsi, model)

    model_store = _get_model_store_cached(complete_conf)
    model_store.update_model_metrics(model_conf, test_metrics)

    logger.info('Retested existing model %s, version %s, new metrics %s',
                model_conf['name'], model_conf['version'], test_metrics)

    return test_metrics


def predict(complete_conf, arg_dict=None):
    logger.debug('Applying model for prediction...')

    dso, dsi = _get_data_sources_and_sinks_cached(complete_conf, tags='predict')

    model, metadata = _get_model_cached(complete_conf)

    model_conf = complete_conf['model']
    output = model.predict(model_conf, dso, dsi, arg_dict or {})

    return output
