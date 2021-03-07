import React, { Component } from "react";
import MarketplaceItem from "./marketplaceItem.component"

import "./html.component.css"
import "./marketplaceList.component.css"

function MarketplaceList(props) {
    return (
        <div>
            {props.storePlugins.filter( storePlugin => storePlugin.name.toLowerCase().includes(props.filter.toLowerCase())).map( c=> <MarketplaceItem key={c._id} name={c.name} installed={c.installed} githubRepo={c.githubRepo} />) }
        </div>
    )
}

export default MarketplaceList;