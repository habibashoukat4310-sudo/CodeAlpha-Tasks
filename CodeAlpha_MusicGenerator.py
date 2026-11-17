"""Train a small LSTM on a built-in melody and write a generated MIDI file.

The bundled melody keeps the example runnable without downloading a dataset.
For better results, pass a folder of MIDI files with --midi-dir.
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

import torch
from torch import nn
from music21 import chord, converter, instrument, note, stream

SEED_NOTES = [60, 64, 67, 72, 71, 67, 64, 62, 60, 64, 69, 72, 74, 72, 69, 67,
              65, 69, 72, 77, 76, 72, 69, 67, 64, 67, 72, 76, 79, 76, 72, 67]
SEQUENCE_LENGTH = 8


def pitch_token(element) -> str | None:
    """Return a stable token for a note or chord, ignoring rests."""
    if isinstance(element, note.Note):
        return str(element.pitch.midi)
    if isinstance(element, chord.Chord):
        return ".".join(str(p.midi) for p in element.pitches)
    return None


def extract_tokens(midi_path: Path) -> list[str]:
    score = converter.parse(str(midi_path))
    tokens = []
    for element in score.flatten().notes:
        token = pitch_token(element)
        if token:
            tokens.append(token)
    return tokens


def load_corpus(midi_dir: Path | None) -> list[str]:
    if midi_dir is None:
        return [str(pitch) for pitch in SEED_NOTES]
    paths = sorted([*midi_dir.glob("*.mid"), *midi_dir.glob("*.midi")])
    if not paths:
        raise ValueError(f"No .mid or .midi files found in {midi_dir}")
    corpus = []
    for path in paths:
        try:
            corpus.extend(extract_tokens(path))
        except Exception as exc:
            print(f"Skipping {path.name}: {exc}")
    if len(corpus) <= SEQUENCE_LENGTH:
        raise ValueError("The MIDI files did not contain enough readable notes.")
    return corpus


class MelodyLSTM(nn.Module):
    def __init__(self, vocabulary_size: int, hidden_size: int = 128):
        super().__init__()
        self.lstm = nn.LSTM(vocabulary_size, hidden_size, batch_first=True)
        self.dropout = nn.Dropout(0.2)
        self.output = nn.Linear(hidden_size, vocabulary_size)

    def forward(self, sequence):
        result, _ = self.lstm(sequence)
        return self.output(self.dropout(result[:, -1, :]))


def train_model(tokens: list[str], epochs: int, seed: int):
    random.seed(seed)
    torch.manual_seed(seed)
    vocabulary = sorted(set(tokens), key=lambda token: (len(token), token))
    to_index = {token: index for index, token in enumerate(vocabulary)}
    windows = [(tokens[i:i + SEQUENCE_LENGTH], tokens[i + SEQUENCE_LENGTH])
               for i in range(len(tokens) - SEQUENCE_LENGTH)]
    if not windows:
        raise ValueError("The corpus needs at least nine notes.")
    inputs = torch.zeros(len(windows), SEQUENCE_LENGTH, len(vocabulary))
    targets = torch.empty(len(windows), dtype=torch.long)
    for row, (sequence, target) in enumerate(windows):
        for column, token in enumerate(sequence):
            inputs[row, column, to_index[token]] = 1.0
        targets[row] = to_index[target]

    model = MelodyLSTM(len(vocabulary))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    loss_function = nn.CrossEntropyLoss()
    model.train()
    for epoch in range(epochs):
        optimizer.zero_grad()
        loss = loss_function(model(inputs), targets)
        loss.backward()
        optimizer.step()
        if epoch == 0 or (epoch + 1) % max(1, epochs // 5) == 0:
            print(f"Epoch {epoch + 1:>3}/{epochs} | loss {loss.item():.4f}")
    return model, vocabulary, to_index


def generate(model, vocabulary: list[str], to_index: dict[str, int],
             seed_tokens: list[str], length: int, temperature: float) -> list[str]:
    sequence = list(seed_tokens[-SEQUENCE_LENGTH:])
    generated = []
    model.eval()
    with torch.no_grad():
        for _ in range(length):
            encoded = torch.zeros(1, SEQUENCE_LENGTH, len(vocabulary))
            for position, token in enumerate(sequence):
                encoded[0, position, to_index[token]] = 1.0
            logits = model(encoded)[0] / max(temperature, 0.05)
            next_index = int(torch.multinomial(torch.softmax(logits, dim=0), 1).item())
            token = vocabulary[next_index]
            generated.append(token)
            sequence = [*sequence[1:], token]
    return generated


def write_midi(tokens: list[str], output: Path, tempo: int):
    melody = stream.Stream()
    melody.append(instrument.Piano())
    for token in tokens:
        pitches = [int(value) for value in token.split(".")]
        element = note.Note(pitches[0]) if len(pitches) == 1 else chord.Chord(pitches)
        element.quarterLength = 0.5
        melody.append(element)
    melody.write("midi", fp=str(output))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--midi-dir", type=Path, help="Optional folder of MIDI training files")
    parser.add_argument("--output", type=Path, default=Path("generated_output.mid"))
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--length", type=int, default=32, help="Number of generated notes/chords")
    parser.add_argument("--temperature", type=float, default=0.8,
                        help="Higher values make note selection less predictable")
    parser.add_argument("--tempo", type=int, default=100, help="Tempo in beats per minute")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    if args.epochs < 1 or args.length < 1 or args.tempo < 1:
        parser.error("epochs, length, and tempo must be positive")
    try:
        tokens = load_corpus(args.midi_dir)
        model, vocabulary, to_index = train_model(tokens, args.epochs, args.seed)
        result = generate(model, vocabulary, to_index, tokens, args.length, args.temperature)
        write_midi(result, args.output, args.tempo)
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Could not generate MIDI: {exc}\n")
    print(f"Saved {len(result)} generated notes/chords to {args.output.resolve()}")


if __name__ == "__main__":
    main()
