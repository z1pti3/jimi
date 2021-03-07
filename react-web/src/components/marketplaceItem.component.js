import React, { Component } from "react";
import PropTypes from "prop-types";
import { URL } from"../utils/api";

import "./html.component.css"
import "./marketplaceItem.component.css"

function installStorePlugin(pluginName,githubRepo) {
    if (window.confirm('Are you sure you want to install / update '+pluginName+'?')) {
        const requestOptions = {
            method: 'GET',
            credentials: 'include',
        };
        var triggers = fetch(URL()+'plugins/store/install/?pluginName='+pluginName+'&githubRepo='+githubRepo, requestOptions).then(response => {
            if (response.ok) {
                return response.json()
            }
        }).then(json => {
            alert(JSON.stringify(json));
        });
    }
}

function MarketplaceItem(props) {
    return (
        <div className="marketplaceItemContainer">
            <a className="marketplaceLink" href='#' onClick={() => {installStorePlugin(props.name,props.githubRepo)}}>
                <div className="marketplaceItem">
                    <span className="marketplaceTitle">{props.name}</span>
                    <span className="marketplaceInstalled">{!props.installed ? "Not Installed" : "Installed"}</span>
                </div>
            </a>
        </div>
    )
}

MarketplaceItem.propTypes = {
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired
};

export default MarketplaceItem;