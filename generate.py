import streamlit as st
import random
import numpy as np
import json
import tensorflow.keras as keras
import music21 as m21

# Define constants
MAPPING_PATH = "mapping.json"  # Update path if necessary
SEQUENCE_LENGTH = 64

def load_mappings():
    with open(MAPPING_PATH, "r") as fp:
        return json.load(fp)

class Generator:
    def __init__(self, model_path="model.h5"):
        self.model_path = model_path
        self.model = keras.models.load_model(model_path)
        self._mappings = load_mappings()
        self._start_symbols = ["/"] * SEQUENCE_LENGTH

    def generate_song(self, seed, num_steps, max_sequence_length, temperature):
        seed = seed.split()
        melody = seed
        seed = self._start_symbols + seed

        seed = [self._mappings[symbol] for symbol in seed]

        for _ in range(num_steps):
            seed = seed[-max_sequence_length:]
            onehot_seed = keras.utils.to_categorical(seed, num_classes=len(self._mappings))
            onehot_seed = onehot_seed[np.newaxis, ...]
            probabilities = self.model.predict(onehot_seed, verbose=0)[0]
            output_int = self._sample_with_temperature(probabilities, temperature)

            seed.append(output_int)
            output_symbol = [k for k, v in self._mappings.items() if v == output_int][0]

            if output_symbol == "/":
                break

            melody.append(output_symbol)

        return melody

    def _sample_with_temperature(self, probabilities, temperature):
        predictions = np.log(probabilities) / temperature
        probabilities = np.exp(predictions) / np.sum(np.exp(predictions))
        return np.random.choice(range(len(probabilities)), p=probabilities)

    def save_song(self, melody, step_duration=0.25, format="midi", file_name="generated_song.mid"):
        stream = m21.stream.Stream()

        start_symbol = None
        step_counter = 1

        for i, symbol in enumerate(melody):
            if symbol != "_" or i + 1 == len(melody):
                if start_symbol is not None:
                    quarter_length_duration = step_duration * step_counter
                    if start_symbol == "r":
                        m21_event = m21.note.Rest(quarterLength=quarter_length_duration)
                    else:
                        m21_event = m21.note.Note(int(start_symbol), quarterLength=quarter_length_duration)
                    stream.append(m21_event)
                    step_counter = 1
                start_symbol = symbol
            else:
                step_counter += 1

        stream.write(format, file_name)

# Streamlit App
st.title("AI Music Generator")
st.markdown("Generate music using a trained AI model.")

def generate_random_seed():
    notes = [str(random.randint(60, 72)) for _ in range(8)]  # Random pitches between 60 and 72
    return " ".join([note + (" _" if i % 2 == 0 else "") for i, note in enumerate(notes)])

# Initialize the generator
model_path = "model.h5"  # Adjust if necessary
mg = Generator(model_path)

# Interface: Random Seed Generation
if st.button("Generate Random Seed"):
    seed = generate_random_seed()
    st.session_state["seed"] = seed
    st.success("Random seed generated: " + seed)

# Display the seed
seed = st.session_state.get("seed", "60 _ 62 _ 64 _ 65 _ 67 _")
st.text_area("Generated Seed", seed, height=68)

# Parameters
num_steps = st.slider("Number of Steps", 100, 500, 300)
temperature = st.slider("Temperature", 0.5, 2.0, 1.0)

# Generate Music
if st.button("Generate Music"):
    st.info("Generating music... this may take a while.")
    melody = mg.generate_song(seed, num_steps, SEQUENCE_LENGTH, temperature)
    output_file = "generated_song.mid"
    mg.save_song(melody, file_name=output_file)
    st.success("Music generated successfully!")

    # Provide download link
    with open(output_file, "rb") as f:
        st.download_button(label="Download MIDI File", data=f, file_name=output_file, mime="audio/midi")
