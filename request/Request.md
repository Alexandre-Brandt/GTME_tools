# Request

## Data
- File path: Data/transcripts/WhatsApp_BerlinRevOpsChapter_feed.txt
The file is a transcript from a WhatsApp group. This group focuses on Revenue Operations and Go-To-Market topics, questions and best practices. The Whatsapp group started in 2024.

The structure is that each message starts with a timecode notiation (ie [2024-02-12, 4:38:05 PM])
Messages can span several lines on the file.

The name of the person follows the timecode. If the name is directly writen one space after (ie "[2024-02-12, 4:38:05 PM] Taimoor Tariq"), then it means I have this person's contact information in my phone book. If there is a ~ sign, it means the name is provided by the user metadata on Whatsapp.

My own messages will be from "Alexandre"

## Tasks

### Tools Names
I want you to run through the chat thread and pull out all the names of Tools, software programs being mentioned. Make the best effort to reckognize names of companies. Consider that some tools may be written as hyperlink with a URL.

**Output** 
Please create a csv file called revopschat_tools.csv containg 4 columns:
- Tool Name
- Category: only if mentioned
- URL: only if mentioned. Do not attempt to research online)
- Mentioned by: the name of the person

## Statistics
Get me the main stats for the thread.
1. Number of message
2. User with the most message
3. Number of messages from me (Alexandre)

**Output**
Simple markdown file with the 3 KPIs
