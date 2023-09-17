import shutil

def compare_sheet_music_and_audio(sheet_music_dict, audio_dict):
    errors = {}
    error_in_bar = {}
    error_in_note = []

    error_bar_files = []

    error_state = False

    sheet_start_time = 0
    audio_start_time = 0

    bar_num = 0
    note_num = 0

    bars_messed_up = []

    for bar, sheet_notes in sheet_music_dict.items():
        audio_notes = audio_dict.get(bar, {})  # Get audio notes for the corresponding bar
        bar_num += 1
        for sheet_note_key, sheet_note_value in sheet_notes.items():
            note_num += 1
            # Initialize audio_note_key to None
            audio_note_key = None

            for key in audio_notes.keys():
                if sheet_note_key in key:
                    audio_note_key = key
                    break
            audio_note_value = audio_notes.get(audio_note_key, None)  # Get corresponding audio note

            if isinstance(sheet_note_value, list):
                sheet_note_duration = sheet_note_value[0]
                sheet_note_pitch = sheet_note_value[1]

            else:
                sheet_note_duration = sheet_note_value
                sheet_note_pitch = None

            if isinstance(audio_note_value, list):
                audio_note_duration = audio_note_value[0]
                audio_note_pitch = audio_note_value[1]

            else:
                audio_note_duration = audio_note_value
                audio_note_pitch = None

            # print(f'Sheet Music: Key: {sheet_note_key}, Value: {sheet_note_value}, Audio: Key: {audio_note_key}, Value: {audio_note_value}')

            # check if you're supposed to playing when you're resting and vice versa
            if sheet_note_key != audio_note_key:
                error_state = True
                # you're resting when you're supposed to be playing
                if "playing" in sheet_note_key:
                    # print("You're supposed to be playing not resting!")
                    error_in_note.append("You're supposed to be playing not resting!")
                # you're playing when you're supposed to be resting
                elif "resting" in sheet_note_key:
                    # print("You're supposed to be resting not playing!")
                    error_in_note.append("You're supposed to be resting not playing!")

            else:
                # checks duration
                if sheet_note_duration != audio_note_duration:
                    error_state = True
                    if isinstance(sheet_note_value, list) and isinstance(audio_note_value, list):
                        note_dif = sheet_note_value[0] - audio_note_value[0]
                    elif isinstance(sheet_note_value, list) == True and isinstance(audio_note_value, list) == False:
                        note_dif = sheet_note_value[0] - audio_note_value
                    elif isinstance(sheet_note_value, list) == False and isinstance(audio_note_value, list) == True:
                        note_dif = sheet_note_value - audio_note_value[0]
                    else:
                        note_dif = sheet_note_value - audio_note_value
                    # if the difference is positive then the player lasted note shorter than it was supposed to be
                    if note_dif > 0:
                        # print(f"note lasted short by {note_dif} beats")
                        error_in_note.append(f"note lasted short by {note_dif} beats")
                    elif note_dif < 0:
                        # print(f"note lasted longer by {abs(note_dif)} beats")
                        error_in_note.append(f"note lasted longer by {abs(note_dif)} beats")

                # note pitch is not the same
                if sheet_note_pitch != audio_note_pitch:
                    error_state = True
                    # print(f"note pitch is not the same, you played a {audio_note_pitch} when you were supposed to play a {sheet_note_pitch}")
                    error_in_note.append(f"note pitch is not the same, you played a {audio_note_pitch} when you were supposed to play a {sheet_note_pitch}")

                if 'resting' not in sheet_note_key:
                    if sheet_note_key in audio_notes:
                        sheet_start_time = sum(
                            [sheet_notes[k][0] if isinstance(sheet_notes[k], list) else sheet_notes[k] for k in
                             list(sheet_notes.keys())[:list(sheet_notes.keys()).index(sheet_note_key)]])
                        audio_start_time = sum(
                            [audio_notes[k][0] if isinstance(audio_notes[k], list) else audio_notes[k] for k in
                             list(audio_notes.keys())[:list(audio_notes.keys()).index(sheet_note_key)]])

                        # Compare start times, allow a small tolerance for timing discrepancies
                        tolerance = 0.1  # Adjust this value as needed
                        time_difference = sheet_start_time - audio_start_time
                        if abs(time_difference) > tolerance:
                            error_state = True
                            if time_difference > 0:
                                # print(f"You came early by {time_difference} beats")
                                error_in_note.append(f"You came early by {time_difference} beats")
                            else:
                                # print(f"You came late by {abs(time_difference)} beats")
                                error_in_note.append(f"You came late by {abs(time_difference)} beats")
                    # else:
                    #     # print(f"Note {sheet_note_key} in bar {bar} from sheet music is missing in the audio.")

            if "playing" in sheet_note_key:
                error_in_bar[f"playing {note_num}"] = error_in_note
            elif "resting" in sheet_note_key:
                error_in_bar[f"resting {note_num}"] = error_in_note

            error_in_note = []

        errors[f"bar {bar_num}"] = error_in_bar
        error_in_bar = {}




    # print(error_bar_files)


    # copy error bars to bars_messed_up_audio
    # Destination folder path
    destination_folder = "bars_messed_up_audio/"

    # Copy each file to the destination folder
    for source_file in error_bar_files:
        shutil.copy(source_file, destination_folder)

    return errors



