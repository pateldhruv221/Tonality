import music21


def read_sheet_music(musicxml_file):

    # Load the MusicXML file
    score = music21.converter.parse(musicxml_file)

    sheet_music_notes = []
    sheet_music_rhythm = []

    # Iterate through all time signatures in the score
    for time_signature in score.flat.getElementsByClass('TimeSignature'):
        t_sign = time_signature.ratioString
        # print(f"Time Signature: {t_sign}")

    tempo_list = [x for x in t_sign]
    numerator = int(tempo_list[0])
    denominator = int(tempo_list[2])
    beats_per_bar = numerator * (4/denominator)

    rest_state = False
    note_state = False
    note_state_count = 0

    rest_duration = 0

    notes_rhythm = []

    # Iterate through the parts and elements
    for part in score.parts:
        # print(f"Part: {part.partName}")

        # Iterate through all elements in the part
        for index, element in enumerate(part.flat.notesAndRests):
            if element.isNote:
                # return note_state_count back to 0
                note_state_count = 0

                # if a rest was played previously it will add it to the rhythm list
                if rest_state == True:
                    sheet_music_rhythm.append([rest_duration])
                    rest_duration = 0
                    rest_state = False
                # Get the note name (e.g., 'C', 'D', 'E')
                note_name = element.name
                if "-" in note_name:
                    note_name = note_name.replace("-", "b")


                # Get the octave number
                octave = element.octave

                # Combine note and octave
                note_and_octave = note_name + str(octave)

                # Add note and octave to sheet music notes list
                sheet_music_notes.append(note_and_octave)

                # Get the note duration
                duration = element.duration.quarterLength
                notes_rhythm.append(duration)
                note_state = True

                # Add duration of each note

                # print(f"Note: {note_and_octave} Duration: {duration}")

                # # Access dynamics for the note
                # for dynamic in element.expressions:
                #     if dynamic.isDynamicMark:
                #         print(f"Dynamic: {dynamic.text}")
            elif element.isRest:
                # return note_rhythm_list back to being empty
                # print(f"Rest Duration: {element.duration.quarterLength}")
                rest_duration += element.duration.quarterLength
                rest_state = True
                note_state_count += 1
                if note_state and note_state_count == 1:
                    sheet_music_rhythm.append(notes_rhythm)

                if len(part.flat.notesAndRests) == index + 1:
                    sheet_music_rhythm.append([rest_duration])
                    rest_duration = 0
                # return note_rhythm_list back to being empty
                notes_rhythm = []




    # print(sheet_music_rhythm)



    playing_vs_resting_with_notes = {}
    order_num = 0
    index = 0
    for note_num, period in enumerate(sheet_music_rhythm):
        for each_note in period:
            order_num += 1
            if note_num % 2 == 0:
                playing_vs_resting_with_notes[f"playing {order_num}"] = [each_note, sheet_music_notes[index]]
                index += 1
            else:
                playing_vs_resting_with_notes[f"resting {order_num}"] = each_note

    # print(playing_vs_resting_with_notes)

    # organizes the playing_vs_resting dictionary into a nested dictionary that organizes each note into a separate bar
    bars_dict = {}
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
            bars_dict[f'bar {bar_num}'] = cur_bar_dict.copy()
            cur_bar_dict.clear()
            if "playing" in x:
                cur_bar_dict[f'playing {number + 1}'] = [divide_beat, value[1]]

            elif "resting" in x:
                cur_bar_dict[f'resting {number + 1}'] = divide_beat


        elif beats_so_far == beats_per_bar:
            bar_num += 1
            beats_so_far = 0
            cur_bar_dict[x] = value
            bars_dict[f'bar {bar_num}'] = cur_bar_dict.copy()
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
        bars_dict[f'bar {bar_num}'] = cur_bar_dict

    # print(bars_dict)

    return beats_per_bar, bars_dict




















