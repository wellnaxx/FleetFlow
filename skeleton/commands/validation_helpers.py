def validate_params_count(params, min_count, max_count=None):
    count = len(params)
    if max_count is None:
        if count < min_count:
            raise ValueError(f"Invalid number of arguments. Expected at least {min_count}; received: {count}.")
    else:
        if count < min_count or count > max_count:
            raise ValueError(f"Invalid number of arguments. Expected between {min_count} and {max_count}; received: {count}.")
    
def try_parse_float(s):
    try:
        return float(s)
    except:
        raise ValueError('Invalid value for weight. Should be a number.')

def try_parse_int(s):
    try:
        return int(s)
    except:
        raise ValueError('Invalid value for ID. Should be an integer.')
