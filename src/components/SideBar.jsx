import PropTypes from 'prop-types'
import SideNavigation from "@cloudscape-design/components/side-navigation"

const SideBar = (props) => {
  return (
    <SideNavigation
      header={{ href: "/", text: props.title }}
      items={props.items}
    />
  )
}

SideBar.propTypes = {
  title: PropTypes.string,
  items: PropTypes.array
}

export default SideBar;
