import PropTypes from 'prop-types'
import HelpPanel from "@cloudscape-design/components/help-panel";

const ToolsBar = (props) => {
  return (
    <HelpPanel
      header={<h2>{props.title}</h2>}
    >
      <div>
        <p>
          {props.text}
        </p>
      </div>
    </HelpPanel>
  )
}

ToolsBar.propTypes = {
  title: PropTypes.string,
  text: PropTypes.string
}

export default ToolsBar;
