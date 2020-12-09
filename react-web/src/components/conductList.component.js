import React, { Component } from "react";
import ConductItem from "./conductItem.component"

import "./html.component.css"
import "./conductList.component.css"

function ConductList(props) {
    return (
        <div>
            {props.conducts.map(c => <ConductItem key={c.id} name={c.name} />)}
        </div>
    )
}

export default ConductList;