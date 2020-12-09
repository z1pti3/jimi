import React, { Component } from "react";
import PluginItem from "./pluginItem.component"

import "./html.component.css"
import "./pluginList.component.css"

function PluginList(props) {
    return (
        <div>
            {props.plugins.map(c => <PluginItem key={c.id} name={c.name} />)}
        </div>
    )
}

export default PluginList;