import { useState } from 'react'
import { post, get } from 'aws-amplify/api';
import { getUrl } from 'aws-amplify/storage'
import Header from "@cloudscape-design/components/header"
import Form from "@cloudscape-design/components/form"
import FormField from "@cloudscape-design/components/form-field"
import Box from "@cloudscape-design/components/box"
import Button from "@cloudscape-design/components/button"
import Container from "@cloudscape-design/components/container"
import SpaceBetween from "@cloudscape-design/components/space-between"
import Spinner from "@cloudscape-design/components/spinner"
import Alert from "@cloudscape-design/components/alert";
import Grid from "@cloudscape-design/components/grid";
import DateRangePicker from "@cloudscape-design/components/date-range-picker";

import "./SearchPage.css"
import Textarea from "@cloudscape-design/components/textarea";

function MainPage() {

    const [customSummaryPrompt, setCustomSummaryPrompt] = useState("Analyze these images and provide a brief summary of its contents. Focus on the main subjects, actions, and any notable elements in the scene. Keep the summary concise, around 2-3 sentences.")
    const [dateRange, setDateRange] = useState({
        type: "relative",
        amount: 1,
        unit: "year"
    });

    const [isProcessing, setIsProcessing] = useState(false)
    const [alertText, setAlertText] = useState("");
    const [alertType, setAlertType] = useState("");
    const [alertVisible, setAlertVisible] = useState(false)
    const [images, setImages] = useState([]);
    const [summary, setSummary] = useState("");

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

    const summarizeImages = async () => {

        setImages([])

        try {
            setIsProcessing(true)

            const item = {
                customSummaryPrompt: customSummaryPrompt,
                dateRange: dateRange
            };

            const restOperation = post({
                apiName: 'clipcrunchapi',
                path: '/images/summarize',
                options: {
                    body: item
                }
            });

            const { body } = await restOperation.response;
            const response = await body.json();

            console.log('API Response:', response)

            setSummary(response.summary);

            let newImages = []
            for (let image of response.images) {
                const imageResponse = await getUrl({key: image.slice(7)});
                newImages.push(imageResponse.url);
            }

            setImages(newImages)
            setIsProcessing(false)

            if (response.summary === "") {
                setError("No summary found")
            } else if (newImages.length === 0) {
                setError("No images found")
            } else {
                setSuccess("Summary completed.")
            }

        } catch (error) {
            setIsProcessing(false)
            setError("An error occurred processing the summary")
            console.log('POST call failed: ', error);
        }
    }

    return (
        <Box margin={{ bottom: "l", top: "s" }} padding="xxs">
            <Form
                errorText=""
                header={<Header variant="h1">Summarize</Header>}
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
                                <Textarea value={customSummaryPrompt} autoFocus={true}
                                       onChange={({ detail }) => {
                                           setCustomSummaryPrompt(detail.value)
                                       }}
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
                            <Button variant='primary'
                                    disabled={isProcessing || dateRange === null}
                                    onClick={summarizeImages}>
                                {isProcessing ? <Spinner /> : "Summarize"}
                            </Button>
                        </SpaceBetween>
                    </Container>

                    {isProcessing ? <Box textAlign="center"><Spinner size='large' /></Box> :
                        images.length > 0 ?
                            <>
                                <p><strong>Text summary:</strong> {summary}</p>
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
                                                        src={image}
                                                        key={Math.random()}
                                                        style={{width: "100%", height: "100%"}}
                                                    />
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
        </Box>
    )
}

export default MainPage;
