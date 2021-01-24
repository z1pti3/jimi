import React, { Component } from "react";
import PropTypes from "prop-types";

import "./html.component.css"
import "./clusterJobItem.component.css"



function ClusterJobItem(props) {
    var d = new Date(0);
    const now = Date.now()/1000;
    d.setUTCSeconds(props.startTime)
    return (
        <div className="clusterJobItemContainer">
            <div className="clusterJobItem">
                <div className="clusterJobLeft">
                    <p className="clusterJobTitle">{props.name}</p>
                    <br/>
                    <p className="clusterJobLeftItem">id: {props.id}</p>
                    <br/>
                    <p className="clusterJobLeftItem">Server Address: {props.server}</p>
                </div>
                <div className="clusterJobRight">
                    <p className="clusterJobRightItem">Start Time: {d.toLocaleString()}</p>
                </div>
            </div>       
        </div>
    )
}

export default ClusterJobItem;