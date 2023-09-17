import tensorflow as tf
import tensorflow_hub as hub

import librosa

import backend.detecting_playing as detecting_playing
import backend.sheet_music_reader as sheet_music_reader
import backend.compare as compare
import logging

import soundfile as sf
from music21 import note

from IPython.display import Audio, Javascript
from scipy.io import wavfile


from pydub import AudioSegment


def analysis(instrument_pitch, audio_file, musicxml_file):

    logger = logging.getLogger()
    logger.setLevel(logging.ERROR)

    # print("tensorflow: %s" % tf.__version__)
    # print("librosa: %s" % librosa.__version__)

    EXPECTED_SAMPLE_RATE = 16000


    def output2hz(pitch_output):
        # Constants taken from https://tfhub.dev/google/spice/2
        PT_OFFSET = 25.58
        PT_SLOPE = 63.07
        FMIN = 10.0;
        BINS_PER_OCTAVE = 12.0;
        cqt_bin = pitch_output * PT_SLOPE + PT_OFFSET;
        return FMIN * 2.0 ** (1.0 * cqt_bin / BINS_PER_OCTAVE)


    def create_audio_segment(audio_file, start_time, end_time):
        y, sr = librosa.load(audio_file, sr=None)
        segment = y[int(start_time * sr):int(end_time * sr)]
        return segment, sr


    def convert_audio_for_model(user_file, output_file='uploads/converted_audio_file.wav'):
        audio = AudioSegment.from_file(user_file)
        audio = audio.set_frame_rate(EXPECTED_SAMPLE_RATE).set_channels(1)
        audio.export(output_file, format="wav")
        return output_file

    def transpose_notes(notes, instrument_pitch):
        transposed_notes = []

        if instrument_pitch == "C":
            pitch_code = "P1"
        if instrument_pitch == "Bb":
            pitch_code = "M2"
        elif instrument_pitch == "Eb":
            pitch_code = "M9"
        elif instrument_pitch == "F":
            pitch_code = "P5"

        for note_str in notes:
            if "♯" in note_str:
                note_str = note_str.replace("♯", "#")
            elif "♭" in note_str:
                note_str = note_str.replace("♭", 'b')



            n = note.Note(note_str)
            n.transpose(pitch_code, inPlace=True)

            if "E#" in n.nameWithOctave:
                transposed_notes.append(f"F{n.octave}")
            elif "B#" in n.nameWithOctave:
                transposed_notes.append(f"C{n.octave}")
            else:
                transposed_notes.append(n.nameWithOctave)

        return transposed_notes



    beats_per_bar, sheet_music_bars_dict = sheet_music_reader.read_sheet_music(musicxml_file)


    notes = []

    playing_onset_times, rhythm_notes_list = detecting_playing.main(audio_file, beats_per_bar)
    count = 0
    for sub_list in playing_onset_times:
        for num, i in enumerate(sub_list):
            if num == len(sub_list) - 1:
                pass
            else:
                count += 1
                # print(f"start time: {i}, end time: {sub_list[num + 1]}")
                audio_segment, sample_rate = create_audio_segment(audio_file, i, sub_list[num + 1])
                output_file = "uploads/output_audio_segment.wav"  # Output WAV file name
                sf.write(output_file, audio_segment, sample_rate)

                converted_audio_file = convert_audio_for_model(output_file)

                # Loading audio samples from the wav file:
                sample_rate, audio_samples = wavfile.read(converted_audio_file, 'rb')

                # Show some basic information about the audio.
                duration = len(audio_samples) / sample_rate
                # print(f'Sample rate: {sample_rate} Hz')
                # print(f'Total duration: {duration:.2f}s')
                # print(f'Size of the input: {len(audio_samples)}')

                # Let's listen to the wav file.
                Audio(audio_samples, rate=sample_rate)

                MAX_ABS_INT16 = 32768.0

                # converts audio files that int16 format to floats between -1 and 1
                audio_samples = audio_samples / float(MAX_ABS_INT16)

                # Executing the Model
                # Loading the SPICE model
                model = hub.load("https://tfhub.dev/google/spice/2")

                # We now feed the audio to the SPICE tf.hub model to obtain pitch and uncertainty outputs as tensors.
                model_output = model.signatures["serving_default"](tf.constant(audio_samples, tf.float32))

                pitch_outputs = model_output["pitch"]
                uncertainty_outputs = model_output["uncertainty"]

                # 'Uncertainty' basically means the opposite of confidence.
                confidence_outputs = 1.0 - uncertainty_outputs

                # removes all pitch estimates with a confidence less than 0.9
                confidence_outputs = list(confidence_outputs)
                pitch_outputs = [float(x) for x in pitch_outputs]

                indices = range(len(pitch_outputs))
                confident_pitch_outputs = [(i, p)
                                           for i, p, c in zip(indices, pitch_outputs, confidence_outputs) if c >= 0.9]

                # Check if there are confident pitch outputs
                if confident_pitch_outputs:
                    confident_pitch_outputs_x, confident_pitch_outputs_y = zip(*confident_pitch_outputs)

                    confident_pitch_values_hz = [output2hz(p) for p in confident_pitch_outputs_y]
                    # print(confident_pitch_values_hz)

                    each_note = librosa.hz_to_note(confident_pitch_values_hz[0])
                    # print(each_note)

                    notes.append(each_note)
                else:
                    # Handle the case where there are no confident pitch outputs
                    # print("No confident pitch outputs found for this segment.")
                    rhythm_notes_list.pop(num)

    # increases teh octave number by 1 because it is one off
    new_notes = []
    for each in notes:
        new_octave = int(each[-1]) + 1
        new_note = each.replace(each[-1], str(new_octave))
        new_notes.append(new_note)

    notes = new_notes


    transposed_notes = transpose_notes(notes, instrument_pitch)

    # print(rhythm_notes_list)
    # converts 2d list to a dictionary which states the order of playing and resting
    playing_vs_resting_with_notes = {}
    order_num = 0
    index = 0
    for note_num, period in enumerate(rhythm_notes_list):
        for each_note in period:
            order_num += 1
            if note_num % 2 == 0:
                playing_vs_resting_with_notes[f"playing {order_num}"] = [each_note, transposed_notes[index]]
                index += 1
            else:
                playing_vs_resting_with_notes[f"resting {order_num}"] = each_note

    # print(playing_vs_resting_with_notes)

    # organizes the playing_vs_resting dictionary into a nested dictionary that organizes each note into a separate bar
    audio_bars_dict = {}
    cur_bar_dict = {}
    beats_so_far = 0
    bar_num = 0
    for number, x in enumerate(playing_vs_resting_with_notes):
        value = playing_vs_resting_with_notes[x]
        if isinstance(value, list):
            beats_so_far += value[0]
        else:
            beats_so_far += value

        if beats_so_far > beats_per_bar:
            bar_num += 1
            divide_beat = beats_so_far - beats_per_bar
            beats_so_far = divide_beat

            if isinstance(value, list):
                value[0] -= divide_beat
            else:
                value -= divide_beat

            cur_bar_dict[x] = value
            audio_bars_dict[f'bar {bar_num}'] = cur_bar_dict.copy()
            cur_bar_dict.clear()
            if "playing" in x:
                cur_bar_dict[f'playing {number + 1}'] = [divide_beat, value[1]]

            elif "resting" in x:
                cur_bar_dict[f'resting {number + 1}'] = divide_beat


        elif beats_so_far == beats_per_bar:
            bar_num += 1
            beats_so_far = 0
            cur_bar_dict[x] = value
            audio_bars_dict[f'bar {bar_num}'] = cur_bar_dict.copy()
            cur_bar_dict.clear()

        else:
            cur_bar_dict[x] = value


    # After processing all notes, check if the final bar is incomplete and fill it with rests
    if cur_bar_dict:
        value_lists = cur_bar_dict.values()
        beats = []
        for beat in value_lists:
            beats.append(beat[0])
        remaining_beats = beats_per_bar - sum(beats)
        if remaining_beats > 0:
            cur_bar_dict[f'resting {number + 2}'] = remaining_beats
        bar_num += 1
        audio_bars_dict[f'bar {bar_num}'] = cur_bar_dict

    # print(audio_bars_dict)

    errors = compare.compare_sheet_music_and_audio(sheet_music_bars_dict, audio_bars_dict)
    # print(errors)

    # Initialize counters
    playing_count = 0
    resting_count = 0

    # Iterate through the nested dictionary
    for bar, notes in errors.items():
        for no, issues in notes.items():
            if "playing" in no and issues:
                playing_count += 1
            elif "resting" in no and issues:
                resting_count += 1

    # Calculate the total counts
    total_playing = sum(1 for notes in errors.values() for no in notes if "playing" in no)
    total_resting = sum(1 for notes in errors.values() for no in notes if "resting" in no)

    # Calculate percentages
    score = [(playing_count+resting_count)/(total_playing+total_resting)] * 100 if total_playing > 0 and total_resting > 0 else 0
    percent_score = (1 - score[0]) * 100
    print(errors)
    print(f"Your score is {(1 - score[0]) * 100}%")

    return percent_score, errors










