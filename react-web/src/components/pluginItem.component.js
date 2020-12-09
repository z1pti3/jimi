import React, { Component } from "react";
import PropTypes from "prop-types";

import "./html.component.css"
import "./pluginItem.component.css"

function PluginItem(props) {
    return (
        <div>
            {props.name}
            <hr/>
        </div>
    )
}

PluginItem.propTypes = {
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired
};

export default PluginItem;