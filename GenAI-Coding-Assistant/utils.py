def evaluate_code(user_code, func_name, test_input, expected_output):
    try:
        local_env = {}
        exec(user_code, {}, local_env)
        result = local_env[func_name](*test_input if isinstance(test_input, list) else [test_input])
        return result == expected_output, result
    except Exception as e:
        return False, str(e)
