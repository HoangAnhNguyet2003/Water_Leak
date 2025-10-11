from torch import nn

class Encoder(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, dropout, seq_len):
        super(Encoder, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.seq_len = seq_len

        self.lstm_enc = nn.LSTM(input_size=input_size,
                                hidden_size=hidden_size,
                                num_layers=num_layers,
                                dropout=dropout if num_layers > 1 else 0,
                                batch_first=True)

        self.norm_enc = nn.LayerNorm(hidden_size)

    def forward(self, x):
        # out: (batch_size, seq_len, hidden_size)
        # last_h_state: (num_layers, batch_size, hidden_size)
        # last_c_state: (num_layers, batch_size, hidden_size)
        out, (last_h_state, last_c_state) = self.lstm_enc(x)

        out_norm = self.norm_enc(out)

        x_enc = last_h_state[-1] # (batch_size, hidden_size)
        x_enc = x_enc.unsqueeze(1).repeat(1, self.seq_len, 1) # (batch_size, seq_len, hidden_size)

        return x_enc, out_norm

class Decoder(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, dropout, seq_len, use_act):
        super(Decoder, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout = dropout
        self.seq_len = seq_len
        self.use_act = use_act
        self.act = nn.Sigmoid()

        self.norm_dec_input = nn.LayerNorm(hidden_size)

        self.lstm_dec = nn.LSTM(input_size=hidden_size,
                                hidden_size=hidden_size,
                                num_layers=num_layers,
                                dropout=dropout if num_layers > 1 else 0,
                                batch_first=True)

        self.norm_dec_output = nn.LayerNorm(hidden_size)

        self.fc = nn.Linear(hidden_size, input_size)

    def forward(self, z):
        z_norm = self.norm_dec_input(z)
        dec_out, (hidden_state, cell_state) = self.lstm_dec(z_norm)

        dec_out_norm = self.norm_dec_output(dec_out)

        dec_out_final = self.fc(dec_out_norm)
        if self.use_act:
            dec_out_final = self.act(dec_out_final)

        return dec_out_final, hidden_state

class LSTMAE(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, dropout_ratio, seq_len, use_act=True):
        super(LSTMAE, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.dropout_ratio = dropout_ratio
        self.seq_len = seq_len
        self.use_act = use_act

        self.encoder = Encoder(input_size=input_size,
                               hidden_size=hidden_size,
                               num_layers=num_layers,
                               dropout=dropout_ratio,
                               seq_len=seq_len)
        self.decoder = Decoder(input_size=input_size,
                               hidden_size=hidden_size,
                               num_layers=num_layers,
                               dropout=dropout_ratio,
                               seq_len=seq_len,
                               use_act=use_act)

    def forward(self, x, return_last_h=False, return_enc_out=False):
        x_enc, enc_out_full = self.encoder(x)
        x_dec, last_h = self.decoder(x_enc)

        if return_last_h:
            return x_dec, last_h
        elif return_enc_out:
            return x_dec, enc_out_full
        return x_dec
