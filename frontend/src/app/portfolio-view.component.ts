import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute, Params } from '@angular/router';
import { Http } from '@angular/http';
import { Observable } from 'rxjs/Observable';
import 'rxjs/add/operator/map';
import 'rxjs/add/operator/switchMap';

import { PortfolioService } from './portfolio.service';

@Component({
    selector: 'app-root',
    templateUrl: './portfolio-view.component.html',
    styleUrls: ['./app.component.css'],
    providers: [PortfolioService]
})
export class PortfolioViewComponent implements OnInit {
    record;

    constructor(
        private portfolioService: PortfolioService,
        private route: ActivatedRoute) {
    }

    ngOnInit(): void {
        this.route.params
            .map(params => params['id'])
            .switchMap(id => this.portfolioService.getRecord(id))
            .subscribe(record => this.record = record);
    }
}


