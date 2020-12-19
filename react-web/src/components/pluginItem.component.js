import React, { Component } from "react";
import PropTypes from "prop-types";

import "./html.component.css"
import "./pluginItem.component.css"

function PluginItem(props) {
    return (
        <div className="pluginItemContainer">
            <a className="pluginLink" href={"plugin/?pluginName="+props.name}>
                <div className="pluginItem">
                    <span className="pluginTitle">{props.name}</span>
                </div>
            </a>
        </div>
    )
}

PluginItem.propTypes = {
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired
};

export default PluginItem;