import { useState } from 'react'
import { post, get } from 'aws-amplify/api';
import { getUrl } from 'aws-amplify/storage'
import Header from "@cloudscape-design/components/header"
import Form from "@cloudscape-design/components/form"
import FormField from "@cloudscape-design/components/form-field"
import Input from "@cloudscape-design/components/input"
import Box from "@cloudscape-design/components/box"
import Container from "@cloudscape-design/components/container"
import SpaceBetween from "@cloudscape-design/components/space-between"
import Spinner from "@cloudscape-design/components/spinner"
import Alert from "@cloudscape-design/components/alert";
import Grid from "@cloudscape-design/components/grid";
import Select from "@cloudscape-design/components/select";
import Modal from "@cloudscape-design/components/modal";
import Toggle from "@cloudscape-design/components/toggle";
import DateRangePicker from "@cloudscape-design/components/date-range-picker";
import Multiselect from "@cloudscape-design/components/multiselect";
import ReactHlsPlayer from 'react-hls-player';

import "./SearchPage.css"

function MainPage() {

    const [showModal, setShowModal] = useState(false)

    const [searchText, setSearchText] = useState("");
    const [searchImage, setSearchImage] = useState("");
    const [days, setDays] = useState({ label: "365", value: "365" });
    const [confidenceThreshold, setConfidenceThreshold] = useState(0);
    const [maxResults, setMaxResults] = useState(50);
    const [includeSimilarTimestamp, setIncludeSimilarTimestamp] = useState(true)
    const [dateRange, setDateRange] = useState({
        type: "relative",
        amount: 1,
        unit: "year"
    });

    const allOptions = [
        {
            label: "fileupload:video",
            value: "fileupload:video",
        },
        {
            label: "webcam:video",
            value: "webcam:video",
        },
        {
            label: "fileupload:image",
            value: "fileupload:image",
        },
        {
            label: "webcam:image",
            value: "webcam:image",
        },
        {
            label: "unknown",
            value: "unknown",
        },
    ]
    const [
        selectedOptions,
        setSelectedOptions
    ] = useState(allOptions);

    const [streamURL, setStreamURL] = useState("");

    const [isProcessing, setIsProcessing] = useState(false)
    const [alertText, setAlertText] = useState("");
    const [alertType, setAlertType] = useState("");
    const [alertVisible, setAlertVisible] = useState(false)
    const [images, setImages] = useState([]);

    const setError = (message) => {
        setAlertText(message)
        setAlertType("error")
        setAlertVisible(true)
    }

    const setSuccess = (message) => {
        setAlertText(message)
        setAlertType("success")
        setAlertVisible(true)
    }

    const getVideoClipURL = async (timestamp) => {

        try {
            const restOperation = get({
                apiName: 'clipcrunchapi',
                path: '/images/sessionURL',
                options: {
                    queryParams: {
                        timestamp: timestamp
                    }
                }
            });

            const { body } = await restOperation.response;
            const response = await body.json();

            console.log('API Response:', response)

            return response.sessionURL

        } catch (error) {
            setIsProcessing(false)
            setError("An error occurred processing the search")
            console.log('GET call failed: ', error);
        }
    }

    const searchImages = async () => {

        setImages([])

        try {
            if (searchText.trim() || searchImage.trim()) {
                setIsProcessing(true)

                //current doing client side filtering, can be modified to do server side filtering
                const imageSourceFilter = selectedOptions.map(item => item.value)

                const item = {
                    searchText: searchText,
                    searchImage: searchImage,
                    dateRange: dateRange,
                    confidenceThreshold: confidenceThreshold,
                    maxResults: maxResults,
                    includeSimilarTimestamp: includeSimilarTimestamp
                };

                const restOperation = post({
                    apiName: 'clipcrunchapi',
                    path: '/images/search',
                    options: {
                        body: item
                    }
                });

                const { body } = await restOperation.response;
                const response = await body.json();

                console.log('API Response:', response)

                let newImages = []
                for (let image of response.images) {
                    const imageResponse = await getUrl({key: image.file});
                    image.url = imageResponse.url
                    console.log(image)
                    console.log(imageSourceFilter)
                    if (imageSourceFilter.includes(image.source)) {
                        newImages.push(image)
                    }
                }

                setImages(newImages)
                setIsProcessing(false)

                if (newImages.length === 0) {
                    setError("No images found")
                } else {
                    setSuccess("Search completed. Found " + newImages.length + " images")
                }
            }

        } catch (error) {
            setIsProcessing(false)
            setError("An error occurred processing the search")
            console.log('POST call failed: ', error);
        }
    }

    return (
        <Box margin={{ bottom: "l", top: "s" }} padding="xxs">
            <Form
                errorText=""
                header={<Header variant="h1">Search Videos</Header>}
            >
                <SpaceBetween size='m'>
                    <Container>
                        <SpaceBetween size='l'>
                            {
                                alertVisible ?
                                    <Alert
                                        dismissible
                                        type={alertType}
                                        header={alertText} onDismiss={() => { setAlertVisible(false) }}
                                    /> : <></>
                            }

                            <FormField>
                                <Input value={searchImage} type="search" inputMode="search" placeholder="Search via Image" autoFocus={true}
                                       onChange={({ detail }) => {
                                           setSearchImage(detail.value)

                                           if (detail.value.length === 0) {
                                               setImages([])
                                           }
                                       }}
                                       onKeyDown={({ detail }) => {
                                           if (detail.keyCode == 13) {
                                               searchImages()
                                           }
                                       }}
                                />
                            </FormField>
                            <FormField>
                                <Input value={searchText} type="search" inputMode="search" placeholder="Search via Text" autoFocus={true}
                                    onChange={({ detail }) => {
                                        setSearchText(detail.value)

                                        if (detail.value.length === 0) {
                                            setImages([])
                                        }
                                    }}
                                    onKeyDown={({ detail }) => {
                                        if (detail.keyCode == 13) {
                                            searchImages()
                                        }
                                    }}
                                />
                            </FormField>
                            <FormField label="Image Source">
                                <Multiselect
                                    selectedOptions={selectedOptions}
                                    onChange={({ detail }) => setSelectedOptions(detail.selectedOptions)}
                                    options={allOptions}
                                    placeholder="Choose options"
                                    selectedAriaLabel="Selected"
                                />
                            </FormField>
                            <FormField label="Date Range">
                                <DateRangePicker
                                    onChange={({ detail }) => setDateRange(detail.value)}
                                    value={dateRange}
                                    relativeOptions={[
                                        {
                                            key: "previous-30-minutes",
                                            amount: 30,
                                            unit: "minute",
                                            type: "relative"
                                        },
                                        {
                                            key: "previous-1-hour",
                                            amount: 1,
                                            unit: "hour",
                                            type: "relative"
                                        },
                                        { key: "previous-1-day", amount: 1, unit: "day", type: "relative" },
                                        { key: "previous-1-week", amount: 1, unit: "week", type: "relative" },
                                        { key: "previous-1-month", amount: 1, unit: "month", type: "relative" },
                                        { key: "previous-3-months", amount: 3, unit: "month", type: "relative" },
                                        { key: "previous-1-year", amount: 1, unit: "year", type: "relative" },
                                    ]}
                                    isValidRange={(range) => {
                                        if (range.type === "absolute") {
                                            const [startDateWithoutTime] = range.startDate.split("T");
                                            const [endDateWithoutTime] = range.endDate.split("T");
                                            if (!startDateWithoutTime || !endDateWithoutTime) {
                                                return {
                                                    valid: false,
                                                    errorMessage: "The selected date range is incomplete. Select a start and end date for the date range."
                                                };
                                            }
                                            if (new Date(range.startDate) - new Date(range.endDate) > 0) {
                                                return {
                                                    valid: false,
                                                    errorMessage: "The selected date range is invalid. The start date must be before the end date."
                                                };
                                            }
                                        }
                                        return { valid: true };
                                    }}
                                    i18nStrings={{
                                        relativeModeTitle: "Relative range",
                                        absoluteModeTitle: "Absolute range",
                                        relativeRangeSelectionHeading: "Choose a range",
                                        startDateLabel: "Start date",
                                        endDateLabel: "End date",
                                        startTimeLabel: "Start time",
                                        endTimeLabel: "End time",
                                        clearButtonLabel: "Clear and dismiss",
                                        cancelButtonLabel: "Cancel",
                                        applyButtonLabel: "Apply",
                                        formatRelativeRange: (e) => {
                                            const { amount, unit } = e;
                                            const unitString = amount === 1 ? unit : unit + "s";
                                            return `Last ${amount} ${unitString}`;
                                        },
                                        formatUnit: (unit, value) => {
                                            return value === 1 ? unit : unit + "s";
                                        },
                                        dateTimeConstraintText: "For date, use YYYY/MM/DD. For time, use 24-hour format.",
                                        errorIconAriaLabel: "Error",
                                        customRelativeRangeOptionLabel: "Custom range",
                                        customRelativeRangeOptionDescription: "Set a custom range in the past",
                                        customRelativeRangeUnitLabel: "Unit of time",
                                        customRelativeRangeDurationLabel: "Duration",
                                        todayAriaLabel: "Today",
                                        nextMonthAriaLabel: "Next month",
                                        previousMonthAriaLabel: "Previous month",
                                        nextYearAriaLabel: "Next year",
                                        previousYearAriaLabel: "Previous year",
                                        dropdownIconAriaLabel: "Show calendar",
                                    }}
                                    placeholder="Filter by a date and time range"
                                />
                            </FormField>
                            <FormField label={"Minimum confidence"}>
                                <Input
                                    onChange={({ detail }) => {
                                        setConfidenceThreshold(detail.value)
                                    }
                                    }
                                    onKeyDown={({ detail }) => {
                                        if (detail.keyCode == 13) {
                                            searchImages()
                                        }
                                    }}
                                    value={confidenceThreshold}
                                    inputMode="numeric"
                                    type="number"
                                />
                            </FormField>
                            <FormField label={"Max Results"}>
                                <Input
                                    onChange={({ detail }) => {
                                        setMaxResults(detail.value)
                                    }
                                    }
                                    onKeyDown={({ detail }) => {
                                        if (detail.keyCode == 13) {
                                            searchImages()
                                        }
                                    }}
                                    value={maxResults}
                                    inputMode="numeric"
                                    type="number"
                                />
                            </FormField>
                            <Toggle
                                onChange={({ detail }) =>
                                    setIncludeSimilarTimestamp(detail.checked)
                                }
                                checked={includeSimilarTimestamp}
                            >
                                Include images with similar timestamp
                            </Toggle>
                        </SpaceBetween>
                    </Container>

                    {isProcessing ? <Box textAlign="center"><Spinner size='large' /></Box> :
                        images.length > 0 ?
                            <>
                                <Grid
                                    gridDefinition={images.map(() => (
                                        { colspan: { default: 6, m: 6, l: 4 } }
                                    ))}
                                >
                                    {
                                        images.map(image => (
                                            <Container key={Math.random()}>
                                                <div key={Math.random()}>
                                                    <img
                                                        src={image.url}
                                                        key={Math.random()}
                                                        style={{width: "100%", height: "100%"}}
                                                        onClick={async () => {
                                                            if (__KINESIS_VIDEO_STREAM_INTEGRATION__) {
                                                                const u = await getVideoClipURL(image.timestamp)
                                                                if (u) {
                                                                    setStreamURL(u)
                                                                    setShowModal(true)
                                                                }
                                                            }
                                                        }
                                                        }
                                                    />
                                                    <p>
                                                        <strong>Timestamp:</strong> {new Date(image.timestamp).toLocaleString()}
                                                    </p>
                                                    <p><strong>Confidence:</strong> {image.confidence.toFixed(2)}</p>
                                                    <p><strong>Text summary:</strong> {image.summary}</p>
                                                    <p><strong>Source:</strong> {image.source}</p>
                                                    {image.custom_metadata !== "No custom metadata available" && (
                                                        <p><strong>Custom metadata:</strong> {image.custom_metadata}</p>
                                                    )}
                                                </div>
                                            </Container>
                                        ))
                                    }
                                </Grid>
                            </>
                            : <></>
                    }

                </SpaceBetween>

            </Form>
            <Modal
                onDismiss={() => {
                    setShowModal(false)
                    setStreamURL("")
                }}
                visible={showModal}
                header="Video Clip"
                size='large'
            >
                <Box textAlign='center'>
                    <ReactHlsPlayer
                        src={streamURL}
                        autoPlay={true}
                        controls={true}
                        width="100%"
                        height="auto"
                    />
                </Box>
            </Modal>
        </Box>
    )
}

export default MainPage;
