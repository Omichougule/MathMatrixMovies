import time
import json
import glob
import subprocess
import uuid
import argparse
import re
import os
import cv2
import shutil
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()


def extract_code_blocks(text):
    # Purpose: To extract Python code blocks enclosed in markdown-style triple backticks from a given text.
    #
    # Regular expression pattern: r"```python(.*?)```"
    # - ```python: Matches the literal characters "```python", indicating the start of a Python code block.
    # - (.*?): This is the capturing group.
    #   - .: Matches any character (except newline by default).
    #   - *: Matches the previous character zero or more times.
    #   - ?: Makes the '*' quantifier non-greedy, meaning it matches as few characters as possible
    #        while still allowing the overall pattern to match. This is important for correctly
    #        handling multiple code blocks in the same text.
    # - ```: Matches the literal characters "```", indicating the end of the code block.
    pattern = r"```python(.*?)```"

    # re.DOTALL: This flag makes the '.' special character in the pattern match any character at all,
    # including a newline. This is essential for capturing multi-line code blocks.
    matches = re.findall(pattern, text, re.DOTALL)

    # Returns a list of strings. Each string in the list is an extracted code block
    # (the content within ```python ... ```), without the surrounding fences.
    return matches


GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

genai.configure(api_key=GOOGLE_API_KEY)


def parse_arguments():
    # Purpose: To handle command-line arguments when the script is run directly from the terminal.
    # This allows users to specify video generation parameters without using the Streamlit UI.
    # Note: This function is primarily for standalone script usage;
    # when used as a module by ui.py, these parameters are passed as function arguments to create_math_matrix_movie.

    # Initialize ArgumentParser with a description of the script.
    parser = argparse.ArgumentParser(
        description="Generate a math movie based on the given problem, audience age, and language."
    )

    # Argument: --math_problem
    # Purpose: To specify the math problem or concept the video should explain.
    # Default: "Explain the pythagorean theorem" if not provided.
    parser.add_argument("--math_problem", type=str, default="Explain the pythagorean theorem",
                        help="The math problem to be visualized in the movie.")

    # Argument: --audience_type
    # Purpose: To specify the target audience's age for the video, influencing complexity and style.
    # Default: 10 (representing 10 years old) if not provided.
    parser.add_argument("--audience_type", type=int, default=10,
                        help="The target audience age for the math movie.")

    # Argument: --language
    # Purpose: To set the language for the video's narration.
    # Default: "English" if not provided.
    parser.add_argument("--language", type=str, default="English",
                        help="The language for the movie narration (default is English).")

    # Argument: --voice_label
    # Purpose: To specify the Azure Speech Service voice label for the narration.
    # Default: "en-US-AriaNeural" (a specific English US voice) if not provided.
    parser.add_argument("--voice_label", type=str, default="en-US-AriaNeural",
                        help="The voice label for the narration (default is en-US-AriaNeural).")

    # Parses the arguments provided from the command line (e.g., python create_movie.py --math_problem "Calculus").
    args = parser.parse_args()

    # Returns the parsed arguments as a tuple.
    return args.math_problem, args.audience_type, args.language, args.voice_label


def main():
    # This is the main function called when the script is executed directly
    # (e.g., `python create_movie.py --math_problem "Calculus"`).
    # It's intended for testing or standalone video generation from the command line.

    # Parses command-line arguments to get video parameters.
    # The following line is commented out in the current version of the script.
    # math_problem, audience_type, language, voice_label = parse_arguments()

    # Prints the obtained parameters to the console.
    # These lines are commented out as they depend on the parse_arguments() call above.
    # print(f"Math Problem: {math_problem}")
    # print(f"Audience Type: {audience_type}")
    # print(f"Language: {language}")
    # print(f"Voice Label: {voice_label}")

    # Note: The primary functionality of this module is usually accessed by calling
    # the `create_math_matrix_movie` function from another script (e.g., the Streamlit UI in `ui.py`),
    # not by running this `main` function directly in its current commented-out state.
    pass # The function effectively does nothing as its operational content is commented out.


# MOVIE_PROMPT:
# This is the primary prompt template used to instruct the Generative AI (Gemini)
# on how to create the Manim Python script for the math explanation video.
#
# Key Placeholders:
# - {math_problem}: The specific math concept to be explained (e.g., "Pythagorean theorem").
# - {audience_type}: The target audience, often an age (e.g., "10 year old"), to tailor complexity and style.
# - {language}: The desired language for narration (e.g., "English", "Spanish").
# - {voice_label}: The specific voice to be used for Azure Text-to-Speech (e.g., "en-US-AriaNeural").
#
# Core Instructions to the AI within this prompt:
# - Generate Manim code for a visual and interesting explanation of the {math_problem} for the {audience_type}.
# - Use only Manim's built-in capabilities for all visuals; strictly avoid external files like SVGs, MP3s, or other graphics.
# - Incorporate voiceovers for all narration using `manim_voiceover.services.azure.AzureService`,
#   with the specified {language} and {voice_label}. An example of voiceover usage is provided within the prompt.
# - Ensure proper visual layout: content should be centered or attractively laid out, considering margins.
#   Long sentences in text should be wrapped.
# - Include actual numbers and mathematical formulas where appropriate to facilitate learning.
# - Adhere to good video design principles: elements should fade out appropriately to prevent artifacts;
#   diagrams and text should be clearly labeled and positioned to avoid overlaps or occlusion.
# - If the input {math_problem} is nonsensical or obviously incorrect, the AI is instructed not to generate code.
# - The final output must be a single, complete Python code block for Manim, ready to be executed directly.
MOVIE_PROMPT = """

Can you explain {math_problem} to a {audience_type}? Please be visual and interesting. Consider using a meme if the audience is younger.

Please create python code for a manim video for the same. 

Please do not use any external dependencies like mp3s or svgs or graphics. Do not create any sound effects. 

If you need to draw something, do so using exclusively manim. Always add a title and an outro. Narrate the title and outro.

Please try to visually center or attractively lay out all content. Please also keep the margins in consideration. If a sentence is long please wrap it by splitting it into multiple lines. 

Please add actual numbers and formulae wherever appropriate as we want our audience of {audience_type} to learn math.

Do use voiceovers to narrate the video. The following is an example of how to do that:

```
from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.azure import AzureService


class AzureExample(VoiceoverScene):
    def construct(self):
        self.set_speech_service(
            AzureService(
                voice="en-US-AriaNeural",
                style="newscast-casual",
                global_speed=1.15
            )
        )

        circle = Circle()
        square = Square().shift(2 * RIGHT)

        with self.voiceover(text="This circle is drawn as I speak.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)

        with self.voiceover(text="Let's shift it to the left 2 units.") as tracker:
            self.play(circle.animate.shift(2 * LEFT),
                      run_time=tracker.duration)

        with self.voiceover(text="Now, let's transform it into a square.") as tracker:
            self.play(Transform(circle, square), run_time=tracker.duration)

        with self.voiceover(
            text="You can also change the pitch of my voice like this.",
            prosody={{"pitch": "+40Hz"}},
        ) as tracker:
            pass

        with self.voiceover(text="Thank you for watching."):
            self.play(Uncreate(circle))

        self.wait()
```

The voice for the "{language}" is "{voice_label}". Please use this voice for the narration. 

Please do not use any external dependencies like svgs or mp3s or grpahics since they are not available. Draw with shapes and use colored letters, but keep it simple. There are no external assets. Constraints are liberating. 

First write the script explicitly and refine the contents and then write the code.

Please draw and animate things, using the whole canvas. Use color in a restrained but elegant way, for educational purposes.

Please add actual numbers and formulae wherever appropriate as we want our audience of {audience_type} to learn math. Please do not leave large blank gaps in the video. Make it visual and interesting. PLEASE ENSURE ELEMENTS FADE OUT AT THE APPROPRIATE TIME. DO NOT LEAVE ARTIFACTS ACROSS SCENES AS THEY OVERLAP AND ARE JARRING. WRAP TEXT IF IT IS LONG. FORMAT TABLES CORRECTLY. ENSURE LABELS, FORMULAE, TEXT AND OBJECTS DO NOT OVERLAP OR OCCLUDE EACH OTHER. Be elegant video designer. Scale charts and numbers to fit the screen. And don't let labels run into each other or overlap, or take up poor positions. For example, do not label a triangle side length at the corners, but the middle. Do not write equations that spill across the Y axis bar or X axis bar, etc.

If the input is math that is obviously wrong, do not generate any code.

Please use only manim for the video. Please write ALL the code needed since it will be extracted directly and run from your response. 

Take a deep breath and consider all the requirements carefully, then write the code.


"""

# TRANSLATION_PROMPT:
# This prompt template is designed to instruct the AI to take an existing Manim script
# (presumably with narration in a source language like English) and translate the narration text
# into the specified target {language}. It also instructs the AI to update the
# Azure TTS {voice_label} to match the new language.
#
# Placeholders:
# - {language}: The target language for translation (e.g., "Spanish").
# - {voice_label}: The Azure TTS voice label appropriate for the target {language} (e.g., "es-ES-ElviraNeural").
#
# Note: This prompt is not actively used in the main `create_math_matrix_movie` workflow,
# which handles language selection directly in the MOVIE_PROMPT. However, it's available
# for potential future features, such as translating already generated scripts.
TRANSLATION_PROMPT = """
Ok. now translate the text to {language}, and replace the voice_label for azureservice with {voice_label}. Please write ALL the code in one go so that it can be extracted and run directly.
"""

# Example lines for using specific fonts if needed, though the main prompt discourages non-standard dependencies.
#       hindi_text = Text('नमस्ते', font='Lohit Devanagari')  # Replace 'Lohit Devanagari' with any available Hindi font
#        tamil_text = Text('வணக்கம்', font='Lohit Tamil')  # Replace 'Lohit Tamil' with any available Tamil font
# Create or cleanup existing extracted image frames directory.


def create_frame_output_dir(output_dir):
    # Ensures that the directory specified for storing extracted video frames exists.
    # If the directory does not exist, it will be created.

    # Check if the directory path already exists.
    if not os.path.exists(output_dir):
        # If not, create the directory.
        # os.makedirs will create any necessary parent directories in the path as well if they don't exist.
        os.makedirs(output_dir)


# FRAME_PREFIX: A constant prefix used in the filenames of extracted frames.
FRAME_PREFIX = "_frame"


def extract_frame_from_video(video_file_path, frame_extraction_directory):
    # Purpose: Extracts individual frames from a given video file and saves them as JPEG images
    # in a specified directory. The extraction rate is determined dynamically based on video
    # duration to obtain a manageable number of frames for AI analysis.

    print(
        f"Extracting frames from {video_file_path}. This might take a bit..."
    )

    # Ensure the output directory for frames exists, creating it if necessary.
    create_frame_output_dir(frame_extraction_directory)

    # --- Video Initialization and Properties ---
    # Open the video file using OpenCV.
    vidcap = cv2.VideoCapture(video_file_path)
    # Get the frames per second (FPS) of the video.
    fps = vidcap.get(cv2.CAP_PROP_FPS)
    # Get the total number of frames in the video.
    total_frames_in_video = int(vidcap.get(cv2.CAP_PROP_FRAME_COUNT))
    # Calculate the total duration of the video in seconds.
    duration = total_frames_in_video / fps

    # --- Frame Extraction Rate Logic ---
    # Set a target maximum number of frames to extract for AI analysis.
    max_target_frames = 60
    if duration <= 60:
        # For videos 60 seconds or shorter, the target is to extract a frame every 1 second.
        # frame_extraction_interval_seconds defines the interval in seconds between frame captures.
        frame_extraction_interval_seconds = 1
    else:
        # For longer videos, calculate an interval in seconds to get close to max_target_frames.
        # This aims to distribute the max_target_frames roughly evenly across the video duration.
        frame_extraction_interval_seconds = max(1, int(duration / max_target_frames))

    # --- Frame Processing Loop ---
    # Prepare a prefix for output filenames, derived from the video file's name.
    output_file_prefix = os.path.basename(video_file_path).replace('.', '_')
    saved_frames_count = 0  # Counter for successfully saved frames.
    processed_frames_count = 0 # Counter for frames processed from the video.

    while vidcap.isOpened():
        # Read the next frame. 'success' is a boolean, 'frame_image' is the image data.
        success, frame_image = vidcap.read()
        if not success:  # If no frame is returned (e.g., end of video or error).
            break

        # Current time in seconds for the processed frame.
        current_time_seconds = processed_frames_count / fps

        # Check if the current frame should be saved based on the calculated interval.
        # This condition saves a frame if its second mark is a multiple of frame_extraction_interval_seconds.
        if int(current_time_seconds) % frame_extraction_interval_seconds == 0:
            # To avoid saving multiple frames for the same second mark if FPS > 1,
            # we check if a frame for this second mark has already been saved.
            # This is implicitly handled if only one frame per second mark is processed by this check,
            # or more explicitly, one could track the last_saved_second.
            # For simplicity, this code might save the first frame encountered for a target second.

            # Format the timestamp (MM:SS) for the current frame's filename.
            minutes = int(current_time_seconds // 60)
            seconds = int(current_time_seconds % 60)
            time_string = f"{minutes:02d}:{seconds:02d}"

            # Construct the full path and filename for the extracted frame.
            image_name = f"{output_file_prefix}{FRAME_PREFIX}{time_string}.jpg"
            output_filename = os.path.join(
                frame_extraction_directory, image_name)

            # Save the current frame_image as a JPEG image.
            # Check if a frame for this specific time_string already exists to avoid duplicates from high FPS videos.
            if not os.path.exists(output_filename): # Prevents overwriting if multiple frames fall into the same second tick
                cv2.imwrite(output_filename, frame_image)
                saved_frames_count += 1

        processed_frames_count += 1

    # --- Cleanup and Return ---
    # Release the video capture object.
    vidcap.release()
    print(
        f"Completed video frame extraction!\n\nExtracted: {saved_frames_count} frames.")

    # Return statistics about the extraction process.
    # 'frame_count' here refers to the number of frames actually saved.
    # 'frame_extraction_rate' refers to the interval in seconds.
    return {"video_duration": duration, "frame_count": saved_frames_count, "frame_extraction_rate": frame_extraction_interval_seconds}


class File:
    # Represents a file, typically an extracted video frame, intended for upload to a generative AI service.
    # It stores the file's local path, an optional display name, a timestamp (often derived from video time
    # encoded in the filename), and later, the response from the AI service after the file has been uploaded.

    def __init__(self, file_path: str, display_name: str = None):
        # Initializes a File object.
        #
        # Args:
        #     file_path (str): The local path to the file.
        #     display_name (str, optional): An optional name for display purposes. Defaults to None.

        self.file_path = file_path  # Path to the file on the local filesystem.
        if display_name:
            self.display_name = display_name # Optional display name for the file.

        # Extracts a timestamp from the filename (e.g., "MM:SS" part).
        # Assumes the filename contains a timestamp parsable by the `get_timestamp` function.
        self.timestamp = get_timestamp(file_path)

        # This attribute will hold the response from the AI service after the file is uploaded.
        # It's typically an object or reference that the AI service uses to access the content of the uploaded file.
        self.response = None

    def set_file_response(self, response):
        # Stores the response received from the AI service (e.g., Google's genai API) after uploading this file.
        # This response is necessary to refer to the uploaded file in subsequent AI model prompts.
        #
        # Args:
        #     response: The response object or data from the `genai.upload_file()` call.
        self.response = response


def get_timestamp(filename):
    # Extracts a timestamp string (e.g., "00:00" for MM:SS format) from a frame's filename.
    # It assumes filenames are formatted similarly to 'output_file_prefix_frameMM:SS.jpg',
    # where `FRAME_PREFIX` (a global variable, e.g., "_frame") acts as a key delimiter.

    # Split the filename string by the FRAME_PREFIX.
    # For an expected filename like "some_video_mp4_frame01:23.jpg":
    # parts[0] would be "some_video_mp4"
    # parts[1] would be "01:23.jpg"
    parts = filename.split(FRAME_PREFIX)

    # Validate if the FRAME_PREFIX was found exactly once, implying correct basic structure.
    if len(parts) != 2:
        # If FRAME_PREFIX is not found or found multiple times, the filename format is unexpected.
        # Print an error or log this for debugging if necessary.
        # print(f"Warning: Unexpected filename format for timestamp extraction: {filename}")
        return None  # Indicates that a timestamp could not be parsed.

    # Take the second part (e.g., "01:23.jpg") and split it by the dot '.'
    # to separate the timestamp from the file extension.
    # timestamp_and_extension[0] would be "01:23"
    # timestamp_and_extension[1] would be "jpg"
    timestamp_and_extension = parts[1].split('.')

    # The first part of this split should be the timestamp string.
    # No further validation is done here on the format of the timestamp itself (e.g., ensuring it's ##:##).
    return timestamp_and_extension[0]


def create_python_file(response):
    code_blocks = extract_code_blocks(response.text)
    for block in code_blocks:
        print("Found code block:")
        print(block.strip())
        code = block.strip()
    # exec(code)
    filename = f"MathMovie_{uuid.uuid4().hex[:8]}"

    # Open the file in write mode ('w') which will overwrite the file if it already exists
    with open(f"{filename}.py", 'w') as file:
        file.write(code)
    return filename


def make_request(prompt, files):
    request = [prompt]
    for file in files:
        request.append(file.timestamp)
        request.append(file.response)
    return request


def send_message_with_retries(chat, request, max_retries=3):
    retry_wait = 60  # upped to 60 seconds cos of 504s grr
    for attempt in range(max_retries):
        try:
            response = chat.send_message(request)
            return response
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(retry_wait)
            retry_wait *= 2  # exponential backoff
    raise Exception("Max retries exceeded")


def create_math_matrix_movie(math_problem, audience_type, language="English", voice_label="en-US-AriaNeural"):
    # Check if audience_type is a digit and format it as "x years old", otherwise leave as is
    if str(audience_type).isdigit():
        audience_type = f"{audience_type} year old"

    # Fill up the MOVIE_PROMPT with the provided arguments
    filled_prompt = MOVIE_PROMPT.format(
        math_problem=math_problem, audience_type=audience_type, language=language, voice_label=voice_label)

    # Print the filled prompt to the console
    model = genai.GenerativeModel('gemini-1.5-pro-latest')
    chat = model.start_chat(history=[])

    attempt_count = 0
    success = False

    next_prompt = filled_prompt

    while attempt_count < 8 and not success:
        print(f"attempt #{attempt_count+1} next_prompt: {next_prompt}")
        response = send_message_with_retries(chat, next_prompt)
        print(response.text)
        filename = create_python_file(response)
        command = f"{os.getenv('MANIM_BIN')} -ql {filename}.py --disable_caching"
        result = subprocess.run(command, shell=True,
                                capture_output=True, text=True)
        print(f"result: {result.returncode}")

        if result.returncode == 0:
            success = True
        else:
            attempt_count += 1
            error_prompt = f"Your last code iteration created an error, this is the text of the error: {result.stderr}\nPlease write ALL the code in one go so that it can be extracted and run directly."
            next_prompt = "\n\n" + error_prompt

    if not success:
        print("Failed to generate a successful output after 8 attempts.")
        raise Exception(
            "Failed to generate a successful output after 8 attempts.")

    # call llama3 with response.text, math_problem, audience_type and language ... to generate youtube metadata

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    path_pattern = os.path.join(
        current_script_dir, f"media/videos/{filename}/480p15/*.mp4")
    mp4_files = glob.glob(path_pattern)

    video_file_path = mp4_files[0]
    with open(f"{filename}.py", 'r') as file:
        initial_code = file.read()
    video_url = os.getenv('BASE_URL') + video_file_path.split("media")[1]

    yield {
        "stage": "initial",
        "video_path": video_file_path,
        "video_id": filename,
        "video_url": video_url,
        "original_prompt": filled_prompt,
        "initial_code": initial_code
    }

    frame_extraction_directory = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), f"media/frames/{filename}/")
    frame_stats = extract_frame_from_video(
        video_file_path, frame_extraction_directory)

    files = os.listdir(frame_extraction_directory)
    files = sorted(files)
    files_to_upload = []
    for file in files:
        if file:
            files_to_upload.append(
                File(file_path=os.path.join(frame_extraction_directory, file)))

    print(files_to_upload)
    # Upload the files to the API
    # Only upload a 10 second slice of files to reduce upload time.
    # Change full_video to True to upload the whole video.
    full_video = True

    uploaded_files = []
    print(
        f'Uploading {len(files_to_upload) if full_video else 10} files. This might take a bit...')

    for file in files_to_upload if full_video else files_to_upload[40:50]:
        print(f'Uploading: {file.file_path}...')
        response = genai.upload_file(path=file.file_path)
        file.set_file_response(response)
        uploaded_files.append(file)

    print(f"Completed file uploads!\n\nUploaded: {len(uploaded_files)} files")
    frame_count = frame_stats['frame_count']
    frame_extraction_rate = frame_stats['frame_extraction_rate']
    video_duration = frame_stats['video_duration']

    prompt = """
        Watch the video keyframes, study the code you generated previously and make tweaks to make the video more appealing, if needed. Ask yourself: is there anything wrong with the attached images? How are the text colors, spacing and so on. How are the animations? How is their placement? be extremely terse and focus on actionable insights. This is for an AI video editor.
        
        Remember to:
        - center titles
        - center all action
        - no text should roll off screen
        - no text should be too small
        - no text should be too big
        - diagrams should be labelled correctly
        - diagrams should be placed correctly
        - diagrams should be animated correctly
        - there should not be any artifacts
        - there should not be significant stretches of blank screen
        - leave some padding at the bottom to allow for where subtitles would appear
        
        These frames were extracted at a rate of {frame_extraction_rate} frames per second, for a video of {video_duration} seconds. Keep the video speed 1.15x.
        
        Previous code:
        ```
        {initial_code}
        ```
        
        After enumerating actionable insights tersely, please write updated code. Please write ONE block of ALL Manim code that includes ALL the code needed since it will be extracted directly and run from your response. Do not write any other blocks of code except the final single output manim code block as it will be extracted and run directly from your response.

        Please do not use any external dependencies like svgs or sound effects since they are not available. There are no external assets. 
                
        Remember, your goal is to explain {math_problem} to {audience_type}. Please stick to explaining the right thing in an interesting way appropriate to the audience. The goal is to make a production grade math explainer video that will help viewers quickly and thoroughly learn the concept. You are a great AI video editor and educator. Keep the video speed 1.15x. Thank you so much! Take a deep breath and get it right!
    """

    # Make the LLM request.
    request = make_request(prompt, uploaded_files)
    response = send_message_with_retries(chat, request)
    print(response.text)

    filename = create_python_file(response)
    # Assuming filename is already defined as shown previously
    command = f"{os.getenv('MANIM_BIN')} -ql {filename}.py --disable_caching"
    result = subprocess.run(command, shell=True)

    if result.returncode != 0:
        attempt_count = 0
        success = False
        error_prompt = f"Your last code iteration created an error, this is the text of the error: {result.stderr}\nPlease write ALL the code in one go so that it can be extracted and run directly."
        next_prompt = "\n\n" + error_prompt
        while attempt_count < 8 and not success:
            print(f"attempt #{attempt_count+1} next_prompt: {next_prompt}")
            response = send_message_with_retries(chat, next_prompt)
            print(response.text)
            filename = create_python_file(response)
            command = f"{os.getenv('MANIM_BIN')} -ql {filename}.py --disable_caching"
            result = subprocess.run(command, shell=True,
                                    capture_output=True, text=True)
            print(f"result: {result.returncode}")

            if result.returncode == 0:
                success = True
            else:
                attempt_count += 1
                error_prompt = f"Your last code iteration created an error, this is the text of the error: {result.stderr}\nPlease write ALL the code in one go so that it can be extracted and run directly."
                next_prompt = "\n\n" + error_prompt

    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    path_pattern = os.path.join(
        current_script_dir, f"media/videos/{filename}/480p15/*.mp4")
    mp4_files = glob.glob(path_pattern)

    video_file_path = mp4_files[0]

    with open(f"{filename}.py", 'r') as file:
        final_code = file.read()

    video_url = os.getenv('BASE_URL') + video_file_path.split("media")[1]

    yield {
        "stage": "final",
        "video_path": video_file_path,
        "video_id": filename,
        "video_url": video_url,
        "original_prompt": filled_prompt,
        "final_code": final_code,
    }

    # Write subprocess
if __name__ == "__main__":
    main()
