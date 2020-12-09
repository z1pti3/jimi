import React, { Component } from "react";
import PropTypes from "prop-types";

import "./html.component.css"
import "./conductItem.component.css"

function ConductItem(props) {
    return (
        <div>
            {props.name}
            <hr/>
        </div>
    )
}

ConductItem.propTypes = {
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired
};

export default ConductItem;