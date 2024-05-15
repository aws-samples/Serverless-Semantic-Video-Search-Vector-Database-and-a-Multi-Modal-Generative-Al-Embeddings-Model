#simple script used to prep CreateOpensearchIndexLambdaFunction.py for JSON Cloudformation zip file

python_function_file = open("CreateOpensearchIndexLambdaFunction.py", "r")
new_file = open("tempCloudformationJSONZipFile.txt", "w")
for line in python_function_file:
    #print(line)
    new_line = f'"{line.rstrip()}",\n'
    #print(new_line)
    new_file.write(new_line)
new_file.close()
python_function_file.close()
