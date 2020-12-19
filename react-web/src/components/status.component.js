import React, { Component } from "react";
import ConductItem from "./conductItem.component"

import "./html.component.css"
import "./status.component.css"

function StatusItem(props) {
    const now = Date.now();
    return (
        <div className="statusItemContainer">
            <div className={`statusItem ${props.enabled ? "statusItemEnabled" : ""} ${props.startCheck > 0 ? "statusItemRunning" : ""} ${props.enabled && props.startCheck > 0 && props.startCheck + props.maxDuration < now  ? "statusItemCrashed" : ""} `} title={props.name}>
            </div>       
        </div>
    )
}

function StatusList(props) {
    return (
        <div>
            {props.triggers.map(c => <StatusItem key={c._id} name={c.name} enabled={c.enabled} startCheck={c.startCheck} maxDuration={c.maxDuration} />)}
        </div>
    )
}

export default StatusList;