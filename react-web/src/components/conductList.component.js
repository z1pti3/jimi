import React, { Component } from "react";
import ConductItem from "./conductItem.component"

import "./html.component.css"
import "./conductList.component.css"

function ConductList(props) {
    return (
        <div>
            {props.conducts.filter(conduct => conduct.name.toLowerCase().includes(props.filter.toLowerCase())).map(c => <ConductItem key={c._id} id={c._id} name={c.name} lastUpdateTime={c.lastUpdateTime} deleteConductClickHandler={props.deleteConductClickHandler} />)}
        </div>
    )
}

export default ConductList;