import React, { Component } from "react";
import ConductItem from "./conductItem.component"

import "./html.component.css"
import "./status.component.css"

function StatusItem(props) {
    const now = Date.now()/1000;
    return (
        <div className="statusItemContainer">
            <div className={`statusItem ${props.enabled ? "statusItemEnabled" : ""} ${ ((props.startCheck > 0 && props.startCheck + props.maxDuration < now) || props.lastCheck + 2.5 > now) ? "statusItemRunning" : ""} ${props.enabled && props.startCheck > 0 && props.startCheck + props.maxDuration < now  ? "statusItemCrashed" : ""} `} title={props.name}>
            </div>       
        </div>
    )
}

function StatusList(props) {
    return (
        <div>
            {props.triggers.map(c => <StatusItem key={c._id} name={c.name} enabled={c.enabled} startCheck={c.startCheck} lastCheck={c.lastCheck} maxDuration={c.maxDuration} />)}
        </div>
    )
}

export default StatusList;