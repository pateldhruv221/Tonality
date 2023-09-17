import librosa
import soundfile as sf
from aubio import onset, source
import numpy as np



def save_audio_segment_as_wav(audio_segment, output_file, sample_rate):
    sf.write(output_file, audio_segment, sample_rate)

def create_audio_segment(audio_file, start_time, end_time):
    y, sr = librosa.load(audio_file, sr=None)
    segment = y[int(start_time * sr):int(end_time * sr)]
    return segment

def get_onset_times(file_path, threshold = 0.15, amplitude_threshold = 0.15):
    window_size = 1024  # FFT size
    hop_size = window_size // 4

    sample_rate = 0
    src_func = source(file_path, sample_rate, hop_size)
    sample_rate = src_func.samplerate
    onset_func = onset('energy', window_size, hop_size)
    onset_func.set_threshold(threshold)  # Adjusted threshold here

    duration = float(src_func.duration) / src_func.samplerate

    onset_times = []  # seconds
    onset_amplitudes = []  # corresponding amplitudes
    waveform = []  # waveform data
    while True:  # read frames
        samples, num_frames_read = src_func()
        waveform.extend(samples)  # Collect the waveform data
        if onset_func(samples):
            onset_time = onset_func.get_last_s()
            onset_amplitude = max(samples)  # Get the maximum amplitude in the onset frame
            if onset_amplitude >= amplitude_threshold:  # Check if the amplitude is above the threshold
                onset_times.append(onset_time)
                onset_amplitudes.append(onset_amplitude)
            if onset_time >= duration:
                break
        if num_frames_read < hop_size:
            break

    # Ensure both lists have the same length before iterating
    min_length = min(len(onset_times), len(onset_amplitudes))

    # for i in range(min_length):
    #     print(f"Onset Time: {onset_times[i]:.4f}, Amplitude: {onset_amplitudes[i]:.4f}")

    y, sr = librosa.load(file_path)


    intervals = librosa.effects.split(y, top_db = 30)

    time_intervals = librosa.samples_to_time(intervals, sr=sr)

    # Filter intervals based on threshold amplitude
    filtered_intervals = []

    for interval in intervals:
        interval_audio = y[int(interval[0]):int(interval[1])]  # Extract the audio data for the interval
        interval_amplitude = np.max(np.abs(interval_audio))  # Calculate the maximum amplitude in the interval

        if interval_amplitude >= threshold:
            filtered_intervals.append(interval)

    # Convert the filtered intervals back to time
    time_intervals = librosa.samples_to_time(np.array(filtered_intervals), sr=sr)

    num_onset_not_in_interval = 0
    for time_interval in time_intervals:
        for each_onset in onset_times:
            if time_interval[0] <= each_onset <= time_interval[1]:
                # print(each_onset)
                break
            else:
                num_onset_not_in_interval += 1

        if num_onset_not_in_interval == len(onset_times):
            # If no onset times are in this interval, remove it
            time_intervals = np.delete(time_intervals, np.where((time_intervals == time_interval).all(axis=1)), axis=0)
            num_onset_not_in_interval = 0

        num_onset_not_in_interval = 0

    # print(time_intervals)


    return time_intervals, y, sr, onset_times


def detect_note_by_duration(duration, tempo):
    note_dict = {
        0.25: "Sixteenth",
        0.33: "Triplet",
        0.5: "Eighth",
        0.75: "Dotted Eighth",
        1: "Quarter",
        1.5: "Dotted Quarter",
        2: "Half",
        3: "Dotted Half",
        4: "Whole"
    }
    note_value = duration * (tempo/60)
    closest_note_duration = min(note_dict, key=lambda x: abs(x - note_value))
    # detected_note = note_dict[closest_note_duration]

    return closest_note_duration

def main(audio_file, beats_per_bar):

    time_intervals, y, sr, onset_times = get_onset_times(audio_file)

    # 3. Running the beat default tracker
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)

    tempo = round(tempo)
    # print(f'Estimated tempo: {tempo} beats per minute')


    # print(time_intervals)

    rest_intervals = []
    playing_intervals = []

# creates two separate lists for the intervals of playing and resting

    for num, t in enumerate(time_intervals):
        if num == 0:
            playing_intervals.append([t[0], t[1]])
        else:
            cur_rest_interval = [start, t[0]]
            rest_intervals.append(cur_rest_interval)
            playing_intervals.append([t[0], t[1]])

        start = t[1]

    # print(f"playing intervals: {playing_intervals}")
    # print(f"rest intervals: {rest_intervals}")

    playing_onset_times = []

# creates a list of the start/end times during playing
    for interval in playing_intervals:
        cur_playing_onset_times = []
        for each_time in onset_times:
            if interval[0] <= each_time < interval[1]:
                cur_playing_onset_times.append(each_time)

        cur_playing_onset_times.append(interval[1])
        playing_onset_times.append(cur_playing_onset_times)

    # print(playing_onset_times)

    playing_and_resting_times = playing_onset_times + rest_intervals

    organized_times = sorted(playing_and_resting_times, key=lambda x: x[0])



# creates a list that finds the duration of each note
    cur_duration_list = []
    duration_list = []
    for a in organized_times:
        for loop_num, index in enumerate(a):
            if loop_num != 0:
                duration = index - start_time
                cur_duration_list.append(duration)
            else:
                pass

            start_time = index

        duration_list.append(cur_duration_list)
        cur_duration_list = []

    # print(duration_list)

    # classifies the note based on their duration
    cur_rhythm_notes_list = []
    rhythm_notes_list = []
    for part in duration_list:
        for d in part:
            detected_note = detect_note_by_duration(d, tempo)
            cur_rhythm_notes_list.append(detected_note)
        rhythm_notes_list.append(cur_rhythm_notes_list)
        cur_rhythm_notes_list = []
    # print(rhythm_notes_list)

    return playing_onset_times, rhythm_notes_list


