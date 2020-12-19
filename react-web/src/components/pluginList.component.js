import React, { Component } from "react";
import PluginItem from "./pluginItem.component"

import "./html.component.css"
import "./pluginList.component.css"

function PluginList(props) {
    return (
        <div>
            {props.plugins.filter( plugin => plugin.name.toLowerCase().includes(props.filter.toLowerCase())).map( c=> <PluginItem key={c._id} name={c.name} />) }
        </div>
    )
}

export default PluginList;