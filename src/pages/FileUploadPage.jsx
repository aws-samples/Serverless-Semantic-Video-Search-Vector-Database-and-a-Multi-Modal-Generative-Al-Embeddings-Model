import { useCallback, useRef, useState } from 'react'
import { get } from 'aws-amplify/api';
import Box from "@cloudscape-design/components/box"
import Container from "@cloudscape-design/components/container"
import SpaceBetween from "@cloudscape-design/components/space-between"
import Alert from "@cloudscape-design/components/alert";
import Header from "@cloudscape-design/components/header"
import Form from "@cloudscape-design/components/form"
import Button from "@cloudscape-design/components/button"
import Spinner from "@cloudscape-design/components/spinner"
import Toggle from "@cloudscape-design/components/toggle";
import FileUpload from "@cloudscape-design/components/file-upload";
import { uploadData } from 'aws-amplify/storage';
import { Buffer } from "buffer"

function FileUploadPage() {

    const [fileArray, setfileArray] = useState([]);

    const [alertText, setAlertText] = useState("");
    const [alertType, setAlertType] = useState("");
    const [alertVisible, setAlertVisible] = useState(false)
    const [isUploading, setIsUploading] = useState(false)

    const upload = async () => {
        setIsUploading(true)
        setAlertVisible(false)

        try {
            const result = await Promise.all(fileArray.map(async (file) => {
                    var filename = "fileUploads/" + file.name;

                    const result = await uploadData({
                        key: filename,
                        data: file,
                    }).result;
                    console.log('Succeeded: ', result);
                })
            )

            setAlertText(`Successfully uploaded ${fileArray.length} files`)
            setAlertType("success")
            setAlertVisible(true)
        } catch (error) {
            console.log(fileArray)
            console.log('Error : ', error);
            setAlertText("File(s) failed to upload. Check console log for more information")
            setAlertType("error")
            setAlertVisible(true)
        }

        setIsUploading(false)
        setfileArray([]);
    };

    return (
        <Box margin={{ bottom: "l", top: "s" }} padding="xxs">
            <Form header={<Header variant="h1">File Upload</Header>}>

                <Container>
                    <SpaceBetween size='m'>
                        {
                            alertVisible ?
                                <SpaceBetween size='m'>
                                    <Alert
                                        type={alertType}
                                        header={alertText} onDismiss={() => { setAlertVisible(false) }}
                                    /></SpaceBetween> : <></>
                        }

                        { !isUploading &&
                            <FileUpload
                                onChange={({ detail }) => {
                                        setfileArray(detail.value)
                                        setAlertVisible(false)
                                    }
                                }
                                value={fileArray}
                                i18nStrings={{
                                    uploadButtonText: e =>
                                        e ? "Choose files" : "Choose file",
                                    dropzoneText: e =>
                                        e
                                            ? "Drop files to upload"
                                            : "Drop file to upload",
                                    removeFileAriaLabel: e =>
                                        `Remove file ${e + 1}`,
                                    limitShowFewer: "Show fewer files",
                                    limitShowMore: "Show more files",
                                    errorIconAriaLabel: "Error"
                                }}
                                multiple
                                showFileLastModified
                                showFileSize
                                showFileThumbnail
                                tokenLimit={3}
                            />
                        }


                        <Button variant='primary'
                                disabled={isUploading || fileArray.length === 0}
                                onClick={upload}>
                            {isUploading ? <Spinner /> : "Upload Files"}
                        </Button>
                    </SpaceBetween>
                </Container>
            </Form>
        </Box>
    )
}

export default FileUploadPage;
