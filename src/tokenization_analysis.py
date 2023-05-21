import pandas as pd

def align_surprisal(rt_data: pd.DataFrame, surprisals: pd.DataFrame, word_boundary: str = "", use_lookup: bool = False):
    rt_surprisals = []
    lookup_table = pd.DataFrame()
    lookup_iterator = iter([])
    if use_lookup:
        lookup_table = read_lookup_table()
        lookup_iterator = lookup_table.itertuples(name = None)
        assert len(lookup_table.index) == len(rt_data.index)
    rt_iterator, rt_columns = rt_data.itertuples(name = None), rt_data.columns.values.tolist()
    surprisal_iterator, surprisal_columns = surprisals.itertuples(name = None), surprisals.columns.values.tolist()
    token_index = 0
    while token_index < len(surprisals.index):
        current_word, current_token = next(rt_iterator), next(surprisal_iterator)
        token_index += 1
        current_word, current_token = current_word[1:], current_token[1:] # getting rid of index column
        buffer = {column:value for value, column in zip(current_token[1:], surprisal_columns[1:])}
        if word_boundary and word_boundary in buffer['token']:
            buffer['token'] = buffer['token'][1:].lower() # remove the word boundary character
        ref = current_word[rt_columns.index('token')].lower()
        if use_lookup:
            ref = next(lookup_iterator)[2].lower()
        mismatch = buffer['token'].lower() != ref
        while mismatch:
            current_token = next(surprisal_iterator)[1:]
            token_index += 1
            if use_lookup:
                buffer['token'] += " "
            buffer['token'] += current_token[surprisal_columns.index('token')]
            buffer['surprisal'] += current_token[surprisal_columns.index('surprisal')]
            if not buffer['oov'] and current_token[surprisal_columns.index('oov')]:
                # mark the word as OOV if this is a case for ANY token in the input 
                buffer['oov'] = True
            if buffer['token'] == ref:
                mismatch = False
        buffer['rt'] = current_word[rt_columns.index('RT')]
        buffer['token_uid'] = current_word[rt_columns.index('token_uid')]
        buffer['exclude_rt'] = current_word[rt_columns.index('exclude')]
        if use_lookup:
            # assign it to the word, since its value in the buffer is the morphological tokenization
            buffer['token'] = current_word[rt_columns.index('token')]
        rt_surprisals.append(buffer)
        buffer = {}
    return pd.DataFrame(rt_surprisals)

def word_length(rt_data: pd.DataFrame, token_col: str):
    return rt_data.apply(lambda row: len(row[token_col]), axis = 1)

def join_log_freq(filepath: str, rt_data: pd.DataFrame):
    freq_table = pd.read_table(filepath, delim_whitespace=True, names=('prob', 'word', 'backoff_weight'))
    rt_data = rt_data.merge(freq_table[['prob', 'word']], how = 'left', left_on = 'token', right_on = 'word')
    rt_data.rename(columns={'prob': 'log_freq'}, inplace = True)
    return rt_data

def prev_token_predictors(rt_data: pd.DataFrame):
    rt_data['prev_freq'] = rt_data['log_freq'].shift(1)
    rt_data['prev_len'] = rt_data['word_length'].shift(1)
    rt_data['prev_surprisal'] = rt_data['surprisal'].shift(1)
    return rt_data

def generate_predictors(rt_data: pd.DataFrame):
    rt_data['word_length'] = word_length(rt_data, 'token')
    rt_data = join_log_freq('word_freqs.txt', rt_data)
    rt_data = prev_token_predictors(rt_data)
    return rt_data.dropna()

def read_lookup_table(word_boundary):
    tokenizer_lookup = pd.read_table("morph_lookup.tsv", delimiter = "\t", names = ["token", "morph_tokenization"])
    separate_tokens_by_space = lambda word: " ".join(word.split(word_boundary))
    tokenizer_lookup['morph_tokenization'] = tokenizer_lookup['morph_tokenization'].apply(separate_tokens_by_space)
    return tokenizer_lookup