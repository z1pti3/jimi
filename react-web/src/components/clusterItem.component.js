import React, { Component } from "react";
import PropTypes from "prop-types";

import "./html.component.css"
import "./clusterItem.component.css"



function ClusterJobItem(props) {
    var d = new Date(0);
    const now = Date.now()/1000;
    d.setUTCSeconds(props.lastSyncTime)
    return (
        <div className="clusterItemContainer">
            <div className="clusterItem">
                <div className="clusterLeft">
                    <p className="clusterTitle">{props.systemID} - {props.systemUID}</p>
                    <br/>
                    <p className="clusterLeftItem">Access Address: {props.bindSecure ? "https://" : "http://"}{props.bindAddress}:{props.bindPort}</p>
                    <br/>
                    <p className="clusterLeftItem">Status: {props.lastSyncTime > now - 120 ? "Online" : "Offline" }</p>
                </div>
                <div className="clusterRight">
                    <p className="clusterRightItem">Last Sync: {d.toLocaleString()}</p>
                    <br/>
                    <p className="clusterRightItem">Sync Count: {props.syncCount}</p>
                    <br/>
                    <p className="clusterRightItem">Master: {props.master ? "Yes" : "No"}</p>
                </div>
            </div>       
        </div>
    )
}

export default ClusterJobItem;