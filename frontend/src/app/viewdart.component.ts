import { Component, Input, OnInit } from '@angular/core';
import { ActivatedRoute, Params } from '@angular/router';
import { Http } from '@angular/http';
import { Observable } from 'rxjs/Observable';
import 'rxjs/add/operator/map';

import { DartService } from './dart.service';

@Component({
    selector: 'app-root',
    templateUrl: './viewdart.component.html',
    styleUrls: ['./app.component.css'],
    providers: [DartService]
})
export class ViewDartComponent implements OnInit {
    id: Observable<string>;
    report;

    constructor(
        private dartService: DartService,
        private route: ActivatedRoute) {
    }

    ngOnInit(): void {
        this.id = this.route.snapshot.params['id'];
    }
}

